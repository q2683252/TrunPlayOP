package api

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerDevices(r *gin.RouterGroup) {
	g := r.Group("/devices")
	g.GET("", listDevices)
	g.POST("/discover", discoverDevices)
	g.POST("/add", addDevice)
	g.DELETE("/:device_id", deleteDevice)
	g.GET("/:device_id/status", deviceStatus)
}

func listDevices(c *gin.Context) {
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	devices, err := db.GetDevices(tx)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, devices)
}

func discoverDevices(c *gin.Context) {
	timeout := 5.0
	if t := c.Query("timeout"); t != "" {
		if f, err := strconv.ParseFloat(t, 64); err == nil {
			timeout = f
		}
	}
	dlna := getDlna(c)
	ctx := c.Request.Context()
	devices, err := dlna.StartDiscovery(ctx, time.Duration(timeout*float64(time.Second)))
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	for _, d := range devices {
		_, _ = db.UpsertDevice(tx, d.ID, d.Name, d.Address, d.Type, d.Manufacturer, d.IsOnline, d.LastSeen, d.LocationURL, d.Source)
	}
	_ = tx.Commit()
	list := make([]gin.H, len(devices))
	for i, d := range devices {
		list[i] = gin.H{"id": d.ID, "name": d.Name, "address": d.Address, "type": d.Type, "manufacturer": d.Manufacturer}
	}
	c.JSON(http.StatusOK, gin.H{"message": "Found " + strconv.Itoa(len(devices)) + " devices", "devices": list})
}

func addDevice(c *gin.Context) {
	var body struct {
		Address string `json:"address"`
		Port    int    `json:"port"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	if body.Port == 0 {
		body.Port = 8200
	}
	dlna := getDlna(c)
	discovered, err := dlna.AddDeviceManually(c.Request.Context(), body.Address, body.Port)
	if err != nil || discovered == nil {
		BadRequest(c, "Could not connect to device at "+body.Address+":"+strconv.Itoa(body.Port))
		return
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	dev, err := db.UpsertDevice(tx, discovered.ID, discovered.Name, discovered.Address, discovered.Type, discovered.Manufacturer, true, discovered.LastSeen, discovered.LocationURL, "MANUAL")
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, dev)
}

func deleteDevice(c *gin.Context) {
	deviceID := c.Param("device_id")
	getDlna(c).RemoveDevice(deviceID)
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.DeleteDevice(tx, deviceID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "Device not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Device deleted"})
}

func deviceStatus(c *gin.Context) {
	deviceID := c.Param("device_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	device, err := db.GetDevice(tx, deviceID)
	if err != nil || device == nil {
		NotFound(c, "Device not found")
		return
	}
	_ = tx.Commit()
	online, _ := getDlna(c).CheckDeviceOnline(c.Request.Context(), deviceID)
	tx2, _ := database.Begin()
	_, _ = db.UpdateDevice(tx2, deviceID, map[string]interface{}{"is_online": online})
	tx2.Commit()
	c.JSON(http.StatusOK, gin.H{"device_id": deviceID, "name": device["name"], "is_online": online})
}
