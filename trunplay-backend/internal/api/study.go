package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerStudy(r *gin.RouterGroup) {
	g := r.Group("/study")
	g.GET("/tasks", listStudyTasks)
	g.GET("/tasks/:task_id", getStudyTask)
	g.POST("/tasks", createStudyTask)
	g.PUT("/tasks/:task_id", updateStudyTask)
	g.DELETE("/tasks/:task_id", deleteStudyTask)
	g.POST("/tasks/:task_id/reset", resetStudyTask)
	g.POST("/tasks/:task_id/media", addStudyTaskMedia)
	g.DELETE("/tasks/:task_id/media/:media_id", removeStudyTaskMedia)
	g.POST("/tasks/:task_id/link/:plan_id", linkStudyTaskToPlan)
	g.DELETE("/tasks/:task_id/link/:plan_id", unlinkStudyTaskFromPlan)
}

func listStudyTasks(c *gin.Context) {
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	list, err := db.GetStudyTasks(tx)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, list)
}

func getStudyTask(c *gin.Context) {
	taskID := c.Param("task_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	task, err := db.GetStudyTask(tx, taskID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if task == nil {
		NotFound(c, "Study task not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, task)
}

func createStudyTask(c *gin.Context) {
	var body struct {
		Name       string `json:"name"`
		MediaItems []struct {
			MediaURI   string `json:"media_uri"`
			MediaName  string `json:"media_name"`
			Duration   int64  `json:"duration"`
			SortOrder  int    `json:"sort_order"`
			SourceType string `json:"source_type"`
			ServerID   string `json:"server_id"`
		} `json:"media_items"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	items := make([]db.StudyTaskMediaCreate, len(body.MediaItems))
	for i, m := range body.MediaItems {
		items[i] = db.StudyTaskMediaCreate{
			MediaURI:   m.MediaURI,
			MediaName:  m.MediaName,
			Duration:   m.Duration,
			SortOrder:  m.SortOrder,
			SourceType: m.SourceType,
			ServerID:   m.ServerID,
		}
		if items[i].SourceType == "" {
			items[i].SourceType = "LOCAL"
		}
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	task, err := db.CreateStudyTask(tx, body.Name, items)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, task)
}

func updateStudyTask(c *gin.Context) {
	taskID := c.Param("task_id")
	var body struct {
		Name string `json:"name"`
	}
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
	task, err := db.UpdateStudyTask(tx, taskID, body.Name)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if task == nil {
		NotFound(c, "Study task not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, task)
}

func deleteStudyTask(c *gin.Context) {
	taskID := c.Param("task_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.DeleteStudyTask(tx, taskID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "Study task not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Study task deleted"})
}

func resetStudyTask(c *gin.Context) {
	taskID := c.Param("task_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	task, err := db.ResetStudyTaskProgress(tx, taskID)
	if err != nil || task == nil {
		NotFound(c, "Study task not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Progress reset", "task_id": taskID})
}

func addStudyTaskMedia(c *gin.Context) {
	taskID := c.Param("task_id")
	var body struct {
		MediaURI   string `json:"media_uri"`
		MediaName  string `json:"media_name"`
		Duration   int64  `json:"duration"`
		SortOrder  int    `json:"sort_order"`
		SourceType string `json:"source_type"`
		ServerID   string `json:"server_id"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	m := db.StudyTaskMediaCreate{
		MediaURI:   body.MediaURI,
		MediaName:  body.MediaName,
		Duration:   body.Duration,
		SortOrder:  body.SortOrder,
		SourceType: body.SourceType,
		ServerID:   body.ServerID,
	}
	if m.SourceType == "" {
		m.SourceType = "LOCAL"
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	media, err := db.AddStudyTaskMedia(tx, taskID, m)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if media == nil {
		NotFound(c, "Study task not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, media)
}

func removeStudyTaskMedia(c *gin.Context) {
	taskID := c.Param("task_id")
	mediaID := c.Param("media_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.RemoveStudyTaskMedia(tx, taskID, mediaID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "Media not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Media removed"})
}

func linkStudyTaskToPlan(c *gin.Context) {
	taskID := c.Param("task_id")
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	_, err = db.LinkPlanStudyTask(tx, planID, taskID, 0)
	if err != nil {
		BadRequest(c, err.Error())
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Linked", "plan_id": planID, "task_id": taskID})
}

func unlinkStudyTaskFromPlan(c *gin.Context) {
	taskID := c.Param("task_id")
	planID := c.Param("plan_id")
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	ok, err := db.UnlinkPlanStudyTask(tx, planID, taskID)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !ok {
		NotFound(c, "Link not found")
		return
	}
	_ = tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Unlinked"})
}
