package doctor

import "testing"

func TestSearchRanksSpecialtyAndRegion(t *testing.T) {
	store := &Store{doctors: []Doctor{
		{Name: "Dhaka Medicine", Specialty: "Medicine Specialist", Region: "Dhaka", Chambers: []Chamber{{Phones: []string{"1"}, VisitingHours: "5pm"}}},
		{Name: "Sylhet Medicine", Specialty: "Medicine Specialist", Region: "Sylhet"},
	}}
	got := store.Search([]string{"Medicine"}, "Dhaka", 10)
	if len(got) != 2 || got[0].Name != "Dhaka Medicine" {
		t.Fatalf("expected Dhaka doctor first: %#v", got)
	}
}
