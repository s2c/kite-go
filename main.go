package main

import (
	"fmt"
	// "io/ioutil"
	// "kite-go/helper"
	"kite-go/kiteGo"
	// "strings"
)

const (
	API_KEY     string = "l3zela16irfa6rax"
	REQ_TOKEN   string = "fj962rwmsd7lxmsm2xzk9ogw4qkwf75i" //Constant for this session
	API_SECRET  string = "qefc9t3ovposnzvvy94k3sckna7vwuxs"
	MINUTE      string = "minute"
	THREE_MIN   string = "3minute"
	FIVE_MIN    string = "5minute"
	TEN_MIN     string = "10minute"
	FIFTEEN_MIN string = "15minute"
	THIRTY_MIN  string = "30minute"
	SIXTY_MIN   string = "60minute"
	DAY         string = "day"
)

func main() {

	// REGULATORY REQUIREMENT
	// Go to https://kite.trade/connect/login?api_key=l3zela16irfa6rax to get request token for the day
	fmt.Println("Starting Client")
	client := kiteGo.KiteClient(API_KEY, REQ_TOKEN, API_SECRET)
	client.Login()
	go client.GetHistorical(MINUTE, "259593", "2015-06-01", "2017-06-01", "InverseNifty50.csv")
	go client.GetHistorical(MINUTE, "256265", "2015-06-01", "2017-06-01", "Nifty50.txt")
	var input string
	fmt.Println("Enter to end...")
	fmt.Scanln(&input)

}

//"https://api.kite.trade/instruments/historical/5633/minute?from=2015-12-28&to=2016-01-01&api_key=l3zela16irfa6rax&access_token=7876696363686d6f376a7165776931656f356a67696b6d667232746b38736579"
