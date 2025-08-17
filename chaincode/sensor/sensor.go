package main

import (
	"encoding/json"
	"fmt"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type SensorData struct {
	ID           string  `json:"id"`
	Seq          int     `json:"seq"`
	Temperature  float64 `json:"temperature"`
	Humidity     float64 `json:"humidity"`
	SoilMoisture float64 `json:"soil_moisture"`
	PH           float64 `json:"ph"`
	Light        float64 `json:"light"`
	WaterLevel   float64 `json:"water_level"`
	Timestamp    string  `json:"timestamp"`
	Payload      string  `json:"payload"`
	Writer       string  `json:"writer"`
}

type Device struct {
	ID    string `json:"id"`
	Owner string `json:"owner"`
}

type NetworkEvent struct {
	DeviceID  string `json:"device_id"`
	EventType string `json:"event_type"`
	Timestamp string `json:"timestamp"`
}

// SecurityIncident represents a detected security issue for a device.
type SecurityIncident struct {
	DeviceID    string `json:"device_id"`
	Description string `json:"description"`
	Timestamp   string `json:"timestamp"`
}

// Attestation contains an attestation result for a device.
type Attestation struct {
	DeviceID  string `json:"device_id"`
	Status    string `json:"status"`
	Timestamp string `json:"timestamp"`
}

func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	return nil
}

func (s *SmartContract) RegisterDevice(ctx contractapi.TransactionContextInterface, id string, owner string) error {
	exists, err := s.deviceExists(ctx, id)
	if err != nil {
		return err
	}
	if exists {
		// Allow repeated registration attempts to succeed without modifying
		// existing ledger state so device announces are idempotent.
		return nil
	}
	dev := Device{ID: id, Owner: owner}
	bytes, err := json.Marshal(dev)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState("DEV"+id, bytes)
}

func (s *SmartContract) deviceExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	bytes, err := ctx.GetStub().GetState("DEV" + id)
	if err != nil {
		return false, err
	}
	return bytes != nil, nil
}

func (s *SmartContract) RecordSensorData(ctx contractapi.TransactionContextInterface, id string, seq int, temperature float64, humidity float64, soilMoisture float64, ph float64, light float64, waterLevel float64, timestamp string, payload string) error {
	writer, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return err
	}
	exists, err := s.deviceExists(ctx, id)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}
	readingKey := fmt.Sprintf("SD%s_%d", id, seq)

	// Enforce idempotent re-submission: if the exact payload already exists,
	// consider it a success without writing a new record.
	if existing, err := ctx.GetStub().GetState(readingKey); err != nil {
		return err
	} else if existing != nil {
		var stored SensorData
		if err := json.Unmarshal(existing, &stored); err != nil {
			return err
		}
		incoming := SensorData{
			ID:           id,
			Seq:          seq,
			Temperature:  temperature,
			Humidity:     humidity,
			SoilMoisture: soilMoisture,
			PH:           ph,
			Light:        light,
			WaterLevel:   waterLevel,
			Timestamp:    timestamp,
			Payload:      payload,
			Writer:       writer,
		}
		incomingBytes, err := json.Marshal(incoming)
		if err != nil {
			return err
		}
		if string(existing) == string(incomingBytes) {
			// Exact same payload already recorded
			return nil
		}
		return fmt.Errorf("reading already exists")
	}

	// Enforce monotonic sequence numbers per device
	lastKey := "LAST" + id
	if lastSeqBytes, err := ctx.GetStub().GetState(lastKey); err != nil {
		return err
	} else if lastSeqBytes != nil {
		var lastSeq int
		if err := json.Unmarshal(lastSeqBytes, &lastSeq); err != nil {
			return err
		}
		if seq <= lastSeq {
			return fmt.Errorf("sequence out of order")
		}
	}

	data := SensorData{
		ID:           id,
		Seq:          seq,
		Temperature:  temperature,
		Humidity:     humidity,
		SoilMoisture: soilMoisture,
		PH:           ph,
		Light:        light,
		WaterLevel:   waterLevel,
		Timestamp:    timestamp,
		Payload:      payload,
		Writer:       writer,
	}
	bytes, err := json.Marshal(data)
	if err != nil {
		return err
	}
	if err := ctx.GetStub().PutState(readingKey, bytes); err != nil {
		return err
	}

	lastSeqBytes, err := json.Marshal(seq)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(lastKey, lastSeqBytes)
}

func (s *SmartContract) LogEvent(ctx contractapi.TransactionContextInterface, deviceID string, eventType string, timestamp string) error {
	exists, err := s.deviceExists(ctx, deviceID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}
	ev := NetworkEvent{DeviceID: deviceID, EventType: eventType, Timestamp: timestamp}
	bytes, err := json.Marshal(ev)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("EVT%s_%s", deviceID, timestamp)
	return ctx.GetStub().PutState(key, bytes)
}

func (s *SmartContract) SendMessage(ctx contractapi.TransactionContextInterface, from string, to string, payload string, timestamp string) error {
	okFrom, err := s.deviceExists(ctx, from)
	if err != nil {
		return err
	}
	if !okFrom {
		return fmt.Errorf("sender not registered")
	}
	okTo, err := s.deviceExists(ctx, to)
	if err != nil {
		return err
	}
	if !okTo {
		return fmt.Errorf("receiver not registered")
	}
	msg := struct {
		From      string `json:"from"`
		To        string `json:"to"`
		Payload   string `json:"payload"`
		Timestamp string `json:"timestamp"`
	}{from, to, payload, timestamp}
	bytes, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("MSG%s_%s_%s", from, to, timestamp)
	return ctx.GetStub().PutState(key, bytes)
}

// LogSecurityIncident stores a security incident on the ledger.
func (s *SmartContract) LogSecurityIncident(ctx contractapi.TransactionContextInterface, deviceID string, desc string, timestamp string) error {
	exists, err := s.deviceExists(ctx, deviceID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}
	incident := SecurityIncident{DeviceID: deviceID, Description: desc, Timestamp: timestamp}
	bytes, err := json.Marshal(incident)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("SEC%s_%s", deviceID, timestamp)
	return ctx.GetStub().PutState(key, bytes)
}

// RecordAttestation records an attestation result on the ledger.
func (s *SmartContract) RecordAttestation(ctx contractapi.TransactionContextInterface, deviceID string, status string, timestamp string) error {
	exists, err := s.deviceExists(ctx, deviceID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}
	att := Attestation{DeviceID: deviceID, Status: status, Timestamp: timestamp}
	bytes, err := json.Marshal(att)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("ATT%s_%s", deviceID, timestamp)
	return ctx.GetStub().PutState(key, bytes)
}

func (s *SmartContract) ReadSensorData(ctx contractapi.TransactionContextInterface, id string) (*SensorData, error) {
	bytes, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, err
	}
	if bytes == nil {
		return nil, fmt.Errorf("data not found")
	}
	var data SensorData
	if err := json.Unmarshal(bytes, &data); err != nil {
		return nil, err
	}
	return &data, nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(err.Error())
	}
	if err := chaincode.Start(); err != nil {
		panic(err.Error())
	}
}
