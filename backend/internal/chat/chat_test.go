package chat

import (
	"testing"

	"doctor-nearby-you/backend/internal/doctor"
	"doctor-nearby-you/backend/internal/safety"
)

func TestReplyAsksLocationBeforeSearch(t *testing.T) {
	service := NewService(&doctor.Store{})
	got := service.Reply(Request{Message: "amar jor"})
	if got.SafetyLevel != safety.Normal || len(got.Questions) == 0 {
		t.Fatalf("expected normal response with location question: %#v", got)
	}
}

func TestReplyStopsOnEmergency(t *testing.T) {
	service := NewService(&doctor.Store{})
	got := service.Reply(Request{Message: "buk betha shash nite koshto"})
	if got.SafetyLevel != safety.Emergency || len(got.Doctors) != 0 {
		t.Fatalf("expected emergency response without doctor search: %#v", got)
	}
}
