package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerPlans(r *gin.RouterGroup) {
	g := r.Group("/plans")
	g.GET("", listPlans)
	g.GET("/:plan_id", getPlan)
	g.POST("", createPlan)
	g.PUT("/:plan_id", updatePlan)
	g.DELETE("/:plan_id", deletePlan)
	g.POST("/:plan_id/activate", activatePlan)
	g.POST("/:plan_id/deactivate", deactivatePlan)
	g.POST("/:plan_id/play", playPlan)
	g.POST("/:plan_id/reset-progress", resetPlanProgress)
}

func listPlans(c *gin.Context) {
	skip, _ := strconv.Atoi(c.DefaultQuery("skip", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "100"))
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plans, err := db.GetPlans(tx, skip, limit)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, plans)
}

func getPlan(c *gin.Context) {
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.GetPlan(tx, planID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, plan)
}

func createPlan(c *gin.Context) {
	var body struct {
		Title        string  `json:"title"`
		StartTime    string  `json:"start_time"`
		EndTime      string  `json:"end_time"`
		RepeatDays   string  `json:"repeat_days"`
		SkipHolidays bool    `json:"skip_holidays"`
		DeviceID     *string `json:"device_id"`
		MediaURL     string  `json:"media_url"`
		IsActive     bool    `json:"is_active"`
		PlayMode     string  `json:"play_mode"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	deviceID := ""
	if body.DeviceID != nil {
		deviceID = *body.DeviceID
	}
	if body.PlayMode == "" {
		body.PlayMode = "SEQUENTIAL"
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.CreatePlan(tx, body.Title, body.StartTime, body.EndTime, body.RepeatDays, deviceID, body.MediaURL, body.PlayMode, body.SkipHolidays, body.IsActive)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if plan != nil && plan["is_active"].(bool) {
		sched := getScheduler(c)
		sched.SchedulePlan(plan["id"].(string), plan["title"].(string), body.StartTime, body.RepeatDays, body.SkipHolidays)
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, plan)
}

func updatePlan(c *gin.Context) {
	planID := c.Param("plan_id")
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
	plan, err := db.UpdatePlan(tx, planID, body)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	sched := getScheduler(c)
	if plan["is_active"].(bool) {
		sched.SchedulePlan(plan["id"].(string), plan["title"].(string), plan["start_time"].(string), plan["repeat_days"].(string), plan["skip_holidays"].(bool))
	} else {
		sched.CancelPlan(planID)
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, plan)
}

func deletePlan(c *gin.Context) {
	planID := c.Param("plan_id")
	getScheduler(c).CancelPlan(planID)
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.DeletePlan(tx, planID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "Plan not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Plan deleted"})
}

func activatePlan(c *gin.Context) {
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.GetPlan(tx, planID)
	if err != nil || plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	plan, err = db.UpdatePlan(tx, planID, map[string]interface{}{"is_active": true})
	if err != nil || plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	getScheduler(c).SchedulePlan(plan["id"].(string), plan["title"].(string), plan["start_time"].(string), plan["repeat_days"].(string), plan["skip_holidays"].(bool))
	_ = tx.Commit()
	c.JSON(http.StatusOK, plan)
}

func deactivatePlan(c *gin.Context) {
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.UpdatePlan(tx, planID, map[string]interface{}{"is_active": false})
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	getScheduler(c).CancelPlan(planID)
	_ = tx.Commit()
	c.JSON(http.StatusOK, plan)
}

func playPlan(c *gin.Context) {
	planID := c.Param("plan_id")
	var body struct {
		StartPosition int `json:"start_position"`
	}
	_ = c.ShouldBindJSON(&body)
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.GetPlan(tx, planID)
	if err != nil || plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	_ = tx.Commit()
	tx2, _ := database.Begin()
	success, err := getPlayback(c).StartPlayback(c.Request.Context(), tx2, plan, "MANUAL", body.StartPosition)
	if err != nil {
		tx2.Rollback()
		ServerError(c, err.Error())
		return
	}
	_ = tx2.Commit()
	if !success {
		ServerError(c, "Failed to start playback")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Playback started", "plan_id": planID})
}

func resetPlanProgress(c *gin.Context) {
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.ResetPlanProgress(tx, planID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Progress reset", "plan_id": planID})
}
