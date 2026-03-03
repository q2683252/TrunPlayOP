package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

// smbPortFromServer returns port from server map (db returns int, JSON may give float64/int64).
func smbPortFromServer(server map[string]interface{}) int {
	if server == nil {
		return 445
	}
	switch v := server["port"].(type) {
	case int:
		if v > 0 {
			return v
		}
	case int64:
		if v > 0 {
			return int(v)
		}
	case float64:
		if v > 0 {
			return int(v)
		}
	}
	return 445
}

func registerSmb(r *gin.RouterGroup) {
	g := r.Group("/smb")
	g.GET("/servers", listSmbServers)
	g.POST("/servers", createSmbServer)
	g.PUT("/servers/:server_id", updateSmbServer)
	g.DELETE("/servers/:server_id", deleteSmbServer)
	g.POST("/servers/test", testSmbServer)
	g.GET("/servers/:server_id/shares", listSmbShares)
	g.GET("/servers/:server_id/browse", browseSmb)
	g.POST("/servers/scan", scanSmb)
}

func listSmbServers(c *gin.Context) {
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	list, err := db.GetSmbServers(tx)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, list)
}

func createSmbServer(c *gin.Context) {
	var body struct {
		Name      string `json:"name"`
		Host      string `json:"host"`
		Port      int    `json:"port"`
		Protocol  string `json:"protocol"`
		Username  string `json:"username"`
		Password  string `json:"password"`
		SharePath string `json:"share_path"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	if body.Port == 0 {
		body.Port = 445
	}
	if body.Protocol == "" {
		body.Protocol = "SMB"
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	server, err := db.CreateSmbServer(tx, body.Name, body.Host, body.Port, body.Protocol, body.Username, body.Password, body.SharePath)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, server)
}

func updateSmbServer(c *gin.Context) {
	serverID := c.Param("server_id")
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	server, err := db.UpdateSmbServer(tx, serverID, body)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if server == nil {
		NotFound(c, "SMB server not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, server)
}

func deleteSmbServer(c *gin.Context) {
	serverID := c.Param("server_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.DeleteSmbServer(tx, serverID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "SMB server not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "SMB server deleted"})
}

func testSmbServer(c *gin.Context) {
	var body struct {
		Host     string `json:"host"`
		Port     int    `json:"port"`
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	if body.Port == 0 {
		body.Port = 445
	}
	ok, msg := getSmb(c).TestConnection(c.Request.Context(), body.Host, body.Port, body.Username, body.Password)
	c.JSON(http.StatusOK, gin.H{"success": ok, "message": msg})
}

func listSmbShares(c *gin.Context) {
	serverID := c.Param("server_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	server, err := db.GetSmbServer(tx, serverID)
	if err != nil || server == nil {
		tx.Rollback()
		NotFound(c, "SMB server not found")
		return
	}
	host, _ := server["host"].(string)
	port := smbPortFromServer(server)
	username, _ := server["username"].(string)
	password, _ := server["password"].(string)
	shares, err := getSmb(c).ListShares(c.Request.Context(), host, port, username, password)
	if err != nil {
		tx.Rollback()
		ServerError(c, err.Error())
		return
	}
	_, _ = db.UpdateSmbServerConnection(tx, serverID, len(shares) > 0)
	if err := tx.Commit(); err != nil {
		ServerError(c, err.Error())
		return
	}
	list := make([]gin.H, len(shares))
	for i, s := range shares {
		list[i] = gin.H{"name": s.Name, "path": s.Path}
	}
	c.JSON(http.StatusOK, gin.H{"server_id": serverID, "shares": list})
}

func browseSmb(c *gin.Context) {
	serverID := c.Param("server_id")
	path := c.DefaultQuery("path", "")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	server, err := db.GetSmbServer(tx, serverID)
	if err != nil || server == nil {
		NotFound(c, "SMB server not found")
		return
	}
	host, _ := server["host"].(string)
	port := smbPortFromServer(server)
	username, _ := server["username"].(string)
	password, _ := server["password"].(string)
	sharePath, _ := server["share_path"].(string)
	items, err := getSmb(c).ListFiles(c.Request.Context(), serverID, host, port, username, password, sharePath, path)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	list := make([]gin.H, len(items))
	for i, it := range items {
		list[i] = gin.H{"id": it.ID, "name": it.Name, "path": it.Path, "uri": it.URI, "type": it.Type, "source_type": it.SourceType, "server_id": it.ServerID, "size": it.Size, "last_modified": it.LastModified}
	}
	parentPath := ""
	if path != "" {
		// simple parent: strip last segment
		for j := len(path) - 1; j >= 0; j-- {
			if path[j] == '/' || path[j] == '\\' {
				parentPath = path[:j]
				break
			}
		}
	}
	c.JSON(http.StatusOK, gin.H{"path": path, "parent_path": parentPath, "items": list})
}

func scanSmb(c *gin.Context) {
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	list, err := db.GetSmbServers(tx)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	scanned := 0
	connected := 0
	for _, server := range list {
		serverID, _ := server["id"].(string)
		host, _ := server["host"].(string)
		port := smbPortFromServer(server)
		username, _ := server["username"].(string)
		password, _ := server["password"].(string)
		shares, err := getSmb(c).ListShares(c.Request.Context(), host, port, username, password)
		scanned++
		ok := err == nil && len(shares) > 0
		if ok {
			connected++
		}
		_, _ = db.UpdateSmbServerConnection(tx, serverID, ok)
	}
	if err := tx.Commit(); err != nil {
		ServerError(c, err.Error())
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Scan completed", "scanned": scanned, "connected": connected})
}
