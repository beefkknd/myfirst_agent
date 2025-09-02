curl -X POST -u elastic -H "Content-Type: application/json" -d '{
  "name": "beef-es-key",
  "role_descriptors": {
    "my-role": {
      "cluster": ["all"],
      "index": [
        {
          "names": ["*"],
          "privileges": ["all"]
        }
      ]
    }
  }
}' "http://localhost:9200/_security/api_key"
