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
    ID        string  `json:"id"`
    Temperature float64 `json:"temperature"`
    Humidity    float64 `json:"humidity"`
    Timestamp   string  `json:"timestamp"`
    CID         string  `json:"cid"`
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

func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
    return nil
}

func (s *SmartContract) RegisterDevice(ctx contractapi.TransactionContextInterface, id string, owner string) error {
    exists, err := s.deviceExists(ctx, id)
    if err != nil {
        return err
    }
    if exists {
        return fmt.Errorf("device already registered")
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

func (s *SmartContract) RecordSensorData(ctx contractapi.TransactionContextInterface, id string, temperature float64, humidity float64, timestamp string, cid string) error {
    exists, err := s.deviceExists(ctx, id)
    if err != nil {
        return err
    }
    if !exists {
        return fmt.Errorf("device not registered")
    }
    data := SensorData{ID: id, Temperature: temperature, Humidity: humidity, Timestamp: timestamp, CID: cid}
    bytes, err := json.Marshal(data)
    if err != nil {
        return err
    }
    return ctx.GetStub().PutState(id, bytes)
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