package main

import (
	"bytes"
	"crypto"
	"crypto/rsa"
	"encoding/binary"
	"fmt"
	"math/big"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// AgriTransaction is the compact on-chain format.
type AgriTransaction struct {
	SensorID  uint16
	Timestamp uint32
	Residue1  uint16
	Residue2  uint16
	Residue3  uint16
	Signature [33]byte
}

// SmartContract for precision agriculture.
type SmartContract struct {
	contractapi.Contract
}

// SubmitTransaction verifies signature and stores the transaction bytes.
func (s *SmartContract) SubmitTransaction(ctx contractapi.TransactionContextInterface, txData []byte) error {
	if len(txData) != binary.Size(AgriTransaction{}) {
		return fmt.Errorf("invalid length")
	}
	var tx AgriTransaction
	if err := binary.Read(bytes.NewReader(txData), binary.BigEndian, &tx); err != nil {
		return err
	}
	pubKey, err := getSensorPublicKey(ctx, tx.SensorID)
	if err != nil {
		return err
	}
	hash := crypto.SHA256.New()
	hash.Write(txData[:11]) // sensorID + timestamp + residues
	digest := hash.Sum(nil)
	if err := rsa.VerifyPKCS1v15(pubKey, crypto.SHA256, digest, tx.Signature[:]); err != nil {
		return fmt.Errorf("signature verify failed: %w", err)
	}
	key := fmt.Sprintf("%d-%d", tx.SensorID, tx.Timestamp)
	return ctx.GetStub().PutState(key, txData)
}

// Placeholder for retrieving a sensor public key.
func getSensorPublicKey(ctx contractapi.TransactionContextInterface, id uint16) (*rsa.PublicKey, error) {
	return &rsa.PublicKey{N: new(big.Int).SetInt64(0), E: 65537}, nil
}

func main() {
	cc, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		panic(err)
	}
	if err := cc.Start(); err != nil {
		panic(err)
	}
}
