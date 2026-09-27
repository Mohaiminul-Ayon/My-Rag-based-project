// Package safety catches urgent symptoms before the chat answer is built.
package safety

import "strings"

type Level string

const (
	Normal    Level = "normal"
	Emergency Level = "emergency"
)

func Check(message string) (Level, string) {
	text := strings.ToLower(message)
	if hasAny(text, "chest pain", "buk betha", "বুক ব্যথা") &&
		hasAny(text, "breath", "shash", "শ্বাস", "shortness") {
		return Emergency, "Chest pain with breathing trouble can be urgent. Please go to the nearest emergency department now."
	}
	if hasAny(text, "unconscious", "ogyan", "অজ্ঞান", "severe bleeding", "rokto porche") {
		return Emergency, "This can be an emergency. Please seek immediate medical help."
	}
	if hasAny(text, "stroke", "face droop", "speech problem", "one side weak") {
		return Emergency, "Stroke-like symptoms are urgent. Please go to emergency care immediately."
	}
	return Normal, ""
}

func hasAny(text string, words ...string) bool {
	for _, word := range words {
		if strings.Contains(text, word) {
			return true
		}
	}
	return false
}
