// Package chat turns patient messages into safe doctor-search responses.
package chat

import (
	"fmt"
	"strings"

	"doctor-nearby-you/backend/internal/doctor"
	"doctor-nearby-you/backend/internal/safety"
)

type Request struct {
	Message  string `json:"message"`
	Location string `json:"location"`
}

type Response struct {
	Reply                string          `json:"reply"`
	Questions            []string        `json:"questions,omitempty"`
	SuggestedSpecialties []string        `json:"suggested_specialties,omitempty"`
	Doctors              []doctor.Result `json:"doctors,omitempty"`
	SafetyLevel          safety.Level    `json:"safety_level"`
}

type Service struct {
	store *doctor.Store
}

func NewService(store *doctor.Store) *Service {
	return &Service{store: store}
}

func (s *Service) Reply(req Request) Response {
	level, warning := safety.Check(req.Message)
	if level == safety.Emergency {
		return Response{
			Reply:       warning + " I can help find a doctor after you are safe.",
			SafetyLevel: level,
		}
	}

	specialties := classify(req.Message)
	if strings.TrimSpace(req.Location) == "" {
		return Response{
			Reply:                "Apni kon city/area te achhen? Location dile ami nearby doctor search korte parbo.",
			Questions:            []string{"Apni kon city/area te achhen?", "Symptom kotodin dhore?"},
			SuggestedSpecialties: specialties,
			SafetyLevel:          safety.Normal,
		}
	}

	results := s.store.Search(specialties, req.Location, 5)
	if len(results) == 0 {
		return Response{
			Reply:                fmt.Sprintf("Amar dataset-e %s area-r jonno matching doctor paini. Danger sign thakle nearest hospital emergency te jan.", req.Location),
			Questions:            []string{"Onno nearby city/area diye search korben?"},
			SuggestedSpecialties: specialties,
			SafetyLevel:          safety.Normal,
		}
	}

	return Response{
		Reply:                "Eta diagnosis na. Apnar symptom-er jonno ei specialist type-er doctor dekhano useful hote pare.",
		Questions:            []string{"Symptom kotodin dhore?", "Kono severe pain, breathing problem, or unconsciousness ache?"},
		SuggestedSpecialties: specialties,
		Doctors:              results,
		SafetyLevel:          safety.Normal,
	}
}

func classify(message string) []string {
	text := strings.ToLower(message)
	rules := []struct {
		words       []string
		specialties []string
	}{
		{[]string{"buk", "chest", "heart", "pressure"}, []string{"Cardiology", "Medicine"}},
		{[]string{"pet betha", "pete betha", "stomach pain", "abdominal pain", "gastric"}, []string{"Gastroenterology", "Medicine"}},
		{[]string{"jor", "fever", "body pain", "cough", "kashi"}, []string{"Medicine"}},
		{[]string{"skin", "rash", "chulkani", "চুলকানি"}, []string{"Dermatology"}},
		{[]string{"tooth", "dath", "দাঁত"}, []string{"Dental"}},
		{[]string{"eye", "chokh", "চোখ"}, []string{"Eye"}},
		{[]string{"pregnancy", "pregnant", "গর্ভ", "period"}, []string{"Gynecology"}},
		{[]string{"kidney", "urine", "prosab", "urology"}, []string{"Urology"}},
	}
	for _, rule := range rules {
		for _, word := range rule.words {
			if strings.Contains(text, word) {
				return rule.specialties
			}
		}
	}
	return []string{"Medicine"}
}
