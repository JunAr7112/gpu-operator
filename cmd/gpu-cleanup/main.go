package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

func main() {
	// Set up the Kubernetes clients
	config, err := clientcmd.BuildConfigFromFlags("", "")
	if err != nil {
		log.Fatalf("Failed to build config: %v", err)
	}
	// Create the clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalf("Failed to create clientset: %v", err)
	}
	// List all nodes
	nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Fatalf("Error fetching Nodes: %v", err)
	}
	// Delete the labels
	for _, node := range nodes.Items {
		fmt.Printf("Node: %s\n", node.Name)
		labels := node.Labels
		for key := range labels {
			if strings.Contains(key, "nvidia.com/gpu.deploy") || strings.Contains(key, "nvidia.com/gpu.present") {
				delete(labels, key)
			}
		}
		// Update the node
		_, err = clientset.CoreV1().Nodes().Update(context.TODO(), &node, metav1.UpdateOptions{})
		if err != nil {
			log.Fatalf("Error updating node: %v", err)
		}
	}

}
