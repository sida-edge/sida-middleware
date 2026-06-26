package repository

import (
	"context"
	"log"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
	"github.com/sida-edge/sida-ontology-builder/internal/domain"
)

type OntologyRepository interface {
	UpsertManifest(ctx context.Context, manifest *domain.Manifest) error
	Close(ctx context.Context) error
}

type neo4jRepository struct {
	driver neo4j.DriverWithContext
}

func NewNeo4jRepository(uri, username, password string) (OntologyRepository, error) {
	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(username, password, ""))
	if err != nil {
		return nil, err
	}
	return &neo4jRepository{driver: driver}, nil
}

func (r *neo4jRepository) Close(ctx context.Context) error {
	return r.driver.Close(ctx)
}

func (r *neo4jRepository) UpsertManifest(ctx context.Context, manifest *domain.Manifest) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	enterprise := manifest.Config.Plant.Enterprise
	site := manifest.Config.Plant.Site
	gatewayID := manifest.GatewayID

	rootQuery := `
		MERGE (ent:Enterprise {name: $enterprise})
		MERGE (sit:Site {name: $site})
		SET sit.gateway_id = $gatewayID
		MERGE (ent)-[:POSSUI_SITE]->(sit)
	`
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
		return tx.Run(ctx, rootQuery, map[string]interface{}{
			"enterprise": enterprise, "site": site, "gatewayID": gatewayID,
		})
	})
	if err != nil {
		log.Printf("Error executing root query: %v", err)
		return err
	}

	for areaName, area := range manifest.Config.Plant.Areas {
		for lineName, line := range area.Lines {
			for deviceID, device := range line.Devices {

				equipmentGlobalID := areaName + "_" + lineName + "_" + deviceID

				deviceQuery := `
					MATCH (sit:Site {name: $site})
					MERGE (are:Area {name: $area})
					MERGE (sit)-[:CONTEM_AREA]->(are)
					
					MERGE (lin:Line {name: $line})
					MERGE (are)-[:CONTEM_LINHA]->(lin)

					MERGE (eq:Equipment {global_id: $equipmentGlobalID})

					SET eq.id = $deviceID, 
						eq.name = $deviceID, 
						eq.protocol = $protocol, 
						eq.host = $host, 
						eq.port = $port, 
						eq.endpoint_url = $endpoint_url, 
						eq.enabled = $enabled
						
					MERGE (lin)-[:CONTEM_EQUIPAMENTO]->(eq)
				`
				_, _ = session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
					return tx.Run(ctx, deviceQuery, map[string]interface{}{
						"site": site, "area": areaName, "line": lineName, 
						"deviceID": deviceID, "equipmentGlobalID": equipmentGlobalID, // <-- Passar o parâmetro novo
						"protocol": device.Connection.Protocol, "host": device.Connection.Host,
						"port": device.Connection.Port, "endpoint_url": device.Connection.EndpointURL,
						"enabled": device.Enabled,
					})
				})
				for metricKey, metric := range device.MetricsMapping {
					metricGlobalID := equipmentGlobalID + "_" + metricKey
					metricQuery := `
						MATCH (eq:Equipment {global_id: $equipmentGlobalID})
						
						MERGE (met:Metric {id: $metricGlobalID})
						SET met.name = $metricName, met.data_type = $dataType, met.unit = $unit, 
							met.scale_factor = $scaleFactor, met.register_type = $registerType, 
							met.node_id = $nodeID, met.address_key = $metricKey
							
						MERGE (eq)-[:POSSUI_METRICA]->(met)
					`
					_, _ = session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
						return tx.Run(ctx, metricQuery, map[string]interface{}{
							"equipmentGlobalID": equipmentGlobalID, // <-- Passar o parâmetro novo
							"metricGlobalID": metricGlobalID,
							"metricName": metric.Name, "dataType": metric.DataType, "unit": metric.Unit,
							"scaleFactor": metric.ScaleFactor, "registerType": metric.RegisterType,
							"nodeID": metric.NodeID, "metricKey": metricKey,
						})
					})
				}
			}
		}
	}
	
	log.Println("Ontologia atualizada com sucesso no Neo4j.")
	return nil
}