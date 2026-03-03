package api

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

var videoExt = map[string]bool{"mp4": true, "mkv": true, "avi": true, "mov": true, "wmv": true, "flv": true, "webm": true, "m4v": true, "3gp": true, "ts": true}
var imageExt = map[string]bool{"jpg": true, "jpeg": true, "png": true, "gif": true, "webp": true}
var audioExt = map[string]bool{"mp3": true, "aac": true, "flac": true, "wav": true, "ogg": true, "m4a": true}

func mediaType(name string) string {
	ext := ""
	if i := strings.LastIndex(name, "."); i >= 0 {
		ext = strings.ToLower(name[i+1:])
	}
	if videoExt[ext] {
		return "VIDEO"
	}
	if imageExt[ext] {
		return "IMAGE"
	}
	if audioExt[ext] {
		return "AUDIO"
	}
	return "UNKNOWN"
}

func registerMedia(r *gin.RouterGroup) {
	g := r.Group("/media")
	g.GET("/local", browseLocal)
	g.GET("/smb/:server_id", browseSmbMedia)
}

func browseLocal(c *gin.Context) {
	path := c.DefaultQuery("path", "")
	cfg := getConfig(c)
	roots := cfg.LocalMediaPaths
	if len(roots) == 0 {
		roots = []string{"/mnt", "/tmp", "/root"}
	}
	if path == "" {
		items := make([]gin.H, 0)
		for _, root := range roots {
			if _, err := os.Stat(root); err != nil {
				continue
			}
			items = append(items, gin.H{
				"id":          "local_" + strings.ReplaceAll(root, "/", "_"),
				"name":        filepath.Base(root),
				"path":        root,
				"uri":         "file://" + root,
				"type":        "FOLDER",
				"source_type": "LOCAL",
			})
		}
		c.JSON(http.StatusOK, gin.H{"path": "/", "parent_path": nil, "items": items})
		return
	}
	path, err := filepath.Abs(path)
	if err != nil {
		BadRequest(c, err.Error())
		return
	}
	path, err = filepath.EvalSymlinks(path)
	if err != nil {
		path = filepath.Clean(path)
	}
	allowed := false
	for _, root := range roots {
		rootAbs, _ := filepath.Abs(root)
		rootAbs, _ = filepath.EvalSymlinks(rootAbs)
		if strings.HasPrefix(path, rootAbs) || path == rootAbs {
			allowed = true
			break
		}
	}
	if !allowed {
		BadRequest(c, "Access denied: path outside allowed directories")
		return
	}
	fi, err := os.Stat(path)
	if err != nil {
		NotFound(c, "Path not found")
		return
	}
	if !fi.IsDir() {
		BadRequest(c, "Not a directory")
		return
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	items := make([]gin.H, 0)
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), ".") {
			continue
		}
		full := filepath.Join(path, e.Name())
		info, err := e.Info()
		if err != nil {
			continue
		}
		if e.IsDir() {
			items = append(items, gin.H{
				"id":          "local_" + strings.ReplaceAll(full, "/", "_"),
				"name":        e.Name(),
				"path":        full,
				"uri":         "file://" + full,
				"type":        "FOLDER",
				"source_type": "LOCAL",
			})
		} else {
			t := mediaType(e.Name())
			if t == "UNKNOWN" {
				continue
			}
			size := int64(0)
			if info != nil {
				size = info.Size()
			}
			modTime := int64(0)
			if info != nil {
				modTime = info.ModTime().UnixMilli()
			}
			items = append(items, gin.H{
				"id":            "local_" + strings.ReplaceAll(full, "/", "_"),
				"name":          e.Name(),
				"path":          full,
				"uri":           "file://" + full,
				"type":          t,
				"source_type":   "LOCAL",
				"size":          size,
				"last_modified": modTime,
			})
		}
	}
	parentPath := filepath.Dir(path)
	if parentPath == path {
		parentPath = ""
	}
	var parent interface{} = parentPath
	if parentPath == "" {
		parent = nil
	}
	c.JSON(http.StatusOK, gin.H{"path": path, "parent_path": parent, "items": items})
}

func browseSmbMedia(c *gin.Context) {
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
		for j := len(path) - 1; j >= 0; j-- {
			if path[j] == '/' || path[j] == '\\' {
				parentPath = path[:j]
				break
			}
		}
	}
	var parent interface{} = parentPath
	if parentPath == "" {
		parent = nil
	}
	c.JSON(http.StatusOK, gin.H{"path": path, "parent_path": parent, "items": list})
}
