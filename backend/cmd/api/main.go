package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"

	"doctor-nearby-you/backend/internal/chat"
	"doctor-nearby-you/backend/internal/doctor"
)

func main() {
	dataPath := env("DATA_PATH", "crawler/data/doctors.jsonl")
	port := env("PORT", "8080")

	store, err := doctor.LoadJSONL(dataPath)
	if err != nil {
		log.Fatal(err)
	}
	chatService := chat.NewService(store)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "frontend/index.html")
	})
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /api/doctors/search", func(w http.ResponseWriter, r *http.Request) {
		limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
		if limit == 0 {
			limit = 10
		}
		specialty := r.URL.Query().Get("specialty")
		region := r.URL.Query().Get("region")
		writeJSON(w, http.StatusOK, store.Search([]string{specialty}, region, limit))
	})
	mux.HandleFunc("POST /api/chat", func(w http.ResponseWriter, r *http.Request) {
		var req chat.Request
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Message == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "message is required"})
			return
		}
		writeJSON(w, http.StatusOK, chatService.Reply(req))
	})

	log.Printf("Doctor Nearby You API listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}

func env(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		log.Println(err)
	}
}
