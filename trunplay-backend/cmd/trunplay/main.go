package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/trunplay/trunplay-backend/internal/api"
	"github.com/trunplay/trunplay-backend/internal/config"
	"github.com/trunplay/trunplay-backend/internal/db"
	"github.com/trunplay/trunplay-backend/internal/services"
)

func main() {
	cfg := config.Load()
	os.Setenv("TRUNPLAY_DB_PATH", cfg.DBPath)

	database, err := db.Open()
	if err != nil {
		log.Fatal("open db:", err)
	}
	defer database.Close()
	if err := db.Init(database); err != nil {
		log.Fatal("init db:", err)
	}
	log.Println("Database initialized at", db.DBPath)

	dlna := services.NewDlnaManager()
	smb := services.NewSmbClient()
	sched := services.NewScheduler(cfg.CrontabFile, cfg.TriggerScript)
	mediaSrv := services.NewMediaServer(cfg.MediaPort, smb)
	playback := services.NewPlaybackService(dlna, mediaSrv, smb, database)

	router := api.NewRouter(database, cfg, dlna, smb, sched, playback, mediaSrv)

	apiServer := &http.Server{
		Addr:    "0.0.0.0:" + strconv.Itoa(cfg.APIPort),
		Handler: router,
	}
	go func() {
		log.Println("API listening on", apiServer.Addr)
		if err := apiServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal("api server:", err)
		}
	}()

	mediaMux := http.NewServeMux()
	mediaMux.Handle("/", mediaSrv.Handler())
	mediaHttp := &http.Server{
		Addr:    "0.0.0.0:" + strconv.Itoa(cfg.MediaPort),
		Handler: mediaMux,
	}
	go func() {
		log.Println("Media server listening on", mediaHttp.Addr)
		if err := mediaHttp.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal("media server:", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	apiServer.Shutdown(ctx)
	mediaHttp.Shutdown(ctx)
	smb.CloseAll()
	log.Println("Stopped")
}
