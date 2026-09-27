package main

import (
	"context"
	"fmt"
	"log"
	"math"

	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	client, err := genai.NewClient(ctx, nil)
	if err != nil {
		log.Fatal(err)
	}
	model := "gemini-embedding-2"
	config := &genai.EmbedContentConfig{
		OutputDimensionality: genai.Ptr[int32](768),
	}

	doctorContents := []*genai.Content{
		genai.NewContentFromText(
			"dentist doctor in Dhaka",
			genai.RoleUser,
		),
	}
	doctorResult, err := client.Models.EmbedContent(ctx, model, doctorContents, config)
	if err != nil {
		log.Fatal(err)
	}
	doctorVector := doctorResult.Embeddings[0].Values

	queryContents := []*genai.Content{
		genai.NewContentFromText(
			"I have stomach pain and live in Dhaka",
			genai.RoleUser,
		),
	}
	queryResult, err := client.Models.EmbedContent(ctx, model, queryContents, config)
	if err != nil {
		log.Fatal(err)
	}
	queryVector := queryResult.Embeddings[0].Values

	fmt.Println("Doctor vector:", len(doctorVector))
	fmt.Println("Query vector:", len(queryVector))

	similarity, err := cosineSimilarity(doctorVector, queryVector)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Cosine similarity: %.4f\n", similarity)
}

// cosineSimilarity compares the direction of two vectors; higher means closer.
func cosineSimilarity(a, b []float32) (float64, error) {
	if len(a) == 0 || len(a) != len(b) {
		return 0, fmt.Errorf("vectors must be non-empty and have equal dimensions")
	}

	var dot, normA, normB float64
	for i, valueA := range a {
		aValue, bValue := float64(valueA), float64(b[i])
		dot += aValue * bValue
		normA += aValue * aValue
		normB += bValue * bValue
	}
	if normA == 0 || normB == 0 {
		return 0, fmt.Errorf("cannot compare a zero vector")
	}

	return dot / (math.Sqrt(normA) * math.Sqrt(normB)), nil
}
