package main

import (
	"encoding/json"
	"fmt"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type Reading struct {
	DeviceID     string             `json:"device_id"`
	WindowID     string             `json:"window_id"`
	Stats        map[string]float64 `json:"stats"`
	LastTS       string             `json:"last_ts"`
	ResiduesHash string             `json:"residues_hash,omitempty"`
	Writer       string             `json:"writer_msp"`
}

type Device struct {
	ID    string `json:"id"`
	Owner string `json:"owner"`
}

type Event struct {
	DeviceID   string    `json:"device_id"`
	TS         string    `json:"ts"`
	Type       string    `json:"type"`
	Before     []float64 `json:"before"`
	After      []float64 `json:"after"`
	Thresholds []float64 `json:"thresholds"`
	Writer     string    `json:"writer_msp"`
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

func (s *SmartContract) RecordReading(ctx contractapi.TransactionContextInterface, deviceID string, windowID string, seq int, statsJSON string, lastTS string, residuesHash string) error {
	writer, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return err
	}
	exists, err := s.deviceExists(ctx, deviceID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}

	stats := map[string]float64{}
	if err := json.Unmarshal([]byte(statsJSON), &stats); err != nil {
		return err
	}

	reading := Reading{
		DeviceID:     deviceID,
		WindowID:     windowID,
		Stats:        stats,
		LastTS:       lastTS,
		ResiduesHash: residuesHash,
		Writer:       writer,
	}
	readingBytes, err := json.Marshal(reading)
	if err != nil {
		return err
	}

	key := fmt.Sprintf("reading:%s:%s", deviceID, windowID)

	if existing, err := ctx.GetStub().GetState(key); err != nil {
		return err
	} else if existing != nil {
		if string(existing) == string(readingBytes) {
			return nil
		}
		return fmt.Errorf("reading already exists")
	}

	seqKey := fmt.Sprintf("last_seq:%s", deviceID)
	if lastSeqBytes, err := ctx.GetStub().GetState(seqKey); err != nil {
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

	if err := ctx.GetStub().PutState(key, readingBytes); err != nil {
		return err
	}

	seqBytes, err := json.Marshal(seq)
	if err != nil {
		return err
	}
	if err := ctx.GetStub().PutState(seqKey, seqBytes); err != nil {
		return err
	}

	return ctx.GetStub().SetEvent("ReadingCommitted", []byte(key))
}

func (s *SmartContract) LogEvent(ctx contractapi.TransactionContextInterface, deviceID string, ts string, eventType string, beforeJSON string, afterJSON string, thresholdsJSON string) error {
	exists, err := s.deviceExists(ctx, deviceID)
	if err != nil {
		return err
	}
	if !exists {
		return fmt.Errorf("device not registered")
	}
	writer, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return err
	}

	before := []float64{}
	if beforeJSON != "" {
		if err := json.Unmarshal([]byte(beforeJSON), &before); err != nil {
			return err
		}
	}
	after := []float64{}
	if afterJSON != "" {
		if err := json.Unmarshal([]byte(afterJSON), &after); err != nil {
			return err
		}
	}
	thresholds := []float64{}
	if thresholdsJSON != "" {
		if err := json.Unmarshal([]byte(thresholdsJSON), &thresholds); err != nil {
			return err
		}
	}

	ev := Event{
		DeviceID:   deviceID,
		TS:         ts,
		Type:       eventType,
		Before:     before,
		After:      after,
		Thresholds: thresholds,
		Writer:     writer,
	}
	bytes, err := json.Marshal(ev)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("event:%s:%s", deviceID, ts)

	if existing, err := ctx.GetStub().GetState(key); err != nil {
		return err
	} else if existing != nil {
		if string(existing) == string(bytes) {
			return nil
		}
		return fmt.Errorf("event already exists")
	}

	if err := ctx.GetStub().PutState(key, bytes); err != nil {
		return err
	}

	return ctx.GetStub().SetEvent("EventCommitted", []byte(key))
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

func (s *SmartContract) ReadReading(ctx contractapi.TransactionContextInterface, deviceID string, windowID string) (*Reading, error) {
	key := fmt.Sprintf("reading:%s:%s", deviceID, windowID)
	bytes, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, err
	}
	if bytes == nil {
		return nil, fmt.Errorf("data not found")
	}
	var data Reading
	if err := json.Unmarshal(bytes, &data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *SmartContract) QueryReadings(ctx contractapi.TransactionContextInterface, deviceID string, windowID string) ([]*Reading, error) {
	selector := map[string]interface{}{"selector": map[string]interface{}{"device_id": deviceID}}
	if windowID != "" {
		selector["selector"].(map[string]interface{})["window_id"] = windowID
	}
	queryBytes, err := json.Marshal(selector)
	if err != nil {
		return nil, err
	}
	resultsIterator, err := ctx.GetStub().GetQueryResult(string(queryBytes))
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()
	var results []*Reading
	for resultsIterator.HasNext() {
		resp, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}
		var r Reading
		if err := json.Unmarshal(resp.Value, &r); err != nil {
			return nil, err
		}
		results = append(results, &r)
	}
	return results, nil
}

func (s *SmartContract) QueryEvents(ctx contractapi.TransactionContextInterface, deviceID string, ts string) ([]*Event, error) {
	selector := map[string]interface{}{"selector": map[string]interface{}{"device_id": deviceID}}
	if ts != "" {
		selector["selector"].(map[string]interface{})["ts"] = ts
	}
	queryBytes, err := json.Marshal(selector)
	if err != nil {
		return nil, err
	}
	resultsIterator, err := ctx.GetStub().GetQueryResult(string(queryBytes))
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()
	var results []*Event
	for resultsIterator.HasNext() {
		resp, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}
		var e Event
		if err := json.Unmarshal(resp.Value, &e); err != nil {
			return nil, err
		}
		results = append(results, &e)
	}
	return results, nil
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
