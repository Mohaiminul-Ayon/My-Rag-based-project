// Package doctor owns doctor records and search rules.
package doctor

import (
	"bufio"
	"encoding/json"
	"os"
	"sort"
	"strings"
)

type Doctor struct {
	ID             string    `json:"doctor_id"`
	Name           string    `json:"name"`
	BMDCRegNo      string    `json:"bmdc_reg_no"`
	Qualifications string    `json:"qualifications"`
	Specialty      string    `json:"specialty"`
	Designation    string    `json:"designation"`
	Workplace      string    `json:"workplace"`
	Region         string    `json:"region"`
	Chambers       []Chamber `json:"chambers"`
	SourceURL      string    `json:"source_url"`
}

type Chamber struct {
	Hospital      string   `json:"hospital"`
	Address       string   `json:"address"`
	VisitingHours string   `json:"visiting_hours"`
	Phones        []string `json:"phones"`
}

type Result struct {
	Doctor
	Score int `json:"score"`
}

type Store struct {
	doctors []Doctor
}

func LoadJSONL(path string) (*Store, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var doctors []Doctor
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 64*1024), 4*1024*1024)
	for scanner.Scan() {
		var doctor Doctor
		if err := json.Unmarshal(scanner.Bytes(), &doctor); err != nil {
			return nil, err
		}
		doctors = append(doctors, doctor)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return &Store{doctors: doctors}, nil
}

func (s *Store) Search(specialties []string, region string, limit int) []Result {
	region = fold(region)
	var results []Result
	for _, doctor := range s.doctors {
		score := 0
		doctorSpecialty := fold(doctor.Specialty)
		for _, specialty := range specialties {
			if strings.Contains(doctorSpecialty, fold(specialty)) {
				score += 10
			}
		}
		if region != "" && fold(doctor.Region) == region {
			score += 7
		}
		for _, chamber := range doctor.Chambers {
			if len(chamber.Phones) > 0 {
				score++
			}
			if chamber.VisitingHours != "" {
				score++
			}
		}
		if score > 0 {
			results = append(results, Result{Doctor: doctor, Score: score})
		}
	}
	sort.Slice(results, func(i, j int) bool {
		if results[i].Score == results[j].Score {
			return results[i].Name < results[j].Name
		}
		return results[i].Score > results[j].Score
	})
	if limit > 0 && len(results) > limit {
		return results[:limit]
	}
	return results
}

func fold(value string) string {
	return strings.ToLower(strings.TrimSpace(value))
}
