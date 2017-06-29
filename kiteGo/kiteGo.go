package kiteGo

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"github.com/buger/jsonparser"
	"io/ioutil"
	"kite-go/helper"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	API_ROOT                string        = "https://api.kite.trade"
	TOKEN_URL               string        = "/session/token"
	PARAMETERS              string        = "/parameters"
	USER_MARGINS            string        = "/user/margins/"
	ORDERS                  string        = "/orders"
	TRADES                  string        = "/trades"
	HISTORICAL              string        = "/instruments/historical/"
	MINUTE                  string        = "minute"
	THREE_MIN               string        = "3minute"
	FIVE_MIN                string        = "5minute"
	TEN_MIN                 string        = "10minute"
	FIFTEEN_MIN             string        = "15minute"
	THIRTY_MIN              string        = "30minute"
	SIXTY_MIN               string        = "60minute"
	DAY                     string        = "day"
	EX_CDS                  string        = "CDS"
	EX_NFO                  string        = "NFO"
	EX_BSE                  string        = "BSE"
	EX_BFO                  string        = "BFO"
	EX_NSE                  string        = "NSE"
	EX_MCX                  string        = "MCX"
	POST                    string        = "POST"
	GET                     string        = "GET"
	DEFAULT_TIMEOUT         time.Duration = 7
	DEFAULT_FULLTIME_LAYOUT string        = "2006-01-02T15:04:05-0700"
	DEFAULT_DATE_LAYOUT     string        = "2006-01-02"
)

//User Tokens
type kiteClient struct {
	Client_API_KEY    string
	Client_REQ_TOKEN  string
	Client_API_SECRET string
	Client_ACC_TOKEN  string
	Client_PUB_TOKEN  string
}

//wrapper to ensure there is a default 10 second timeout
func httpClient(timeout time.Duration) *http.Client {
	client := &http.Client{}
	client.Timeout = timeout * time.Second
	return client
}

//Create a new Kite Client
func KiteClient(key string, req string, secret string) *kiteClient {

	k := &kiteClient{}

	k.Client_API_KEY = key
	k.Client_REQ_TOKEN = req
	k.Client_API_SECRET = secret
	k.Client_ACC_TOKEN = ""
	k.Client_PUB_TOKEN = ""

	return k
}

//Set the access token
func (k *kiteClient) SetAccessToken(acc_token string) {
	k.Client_ACC_TOKEN = acc_token
}

func (k *kiteClient) SetPublicToken(pub_token string) {
	k.Client_PUB_TOKEN = pub_token
}

//Login to retrieve access token. API_KEY,REQ_TOKEN, API_SECRET MUST BE SET
func (k *kiteClient) Login() {
	//Compute Hash and store checksum
	hasher := sha256.New()
	checksum := k.Client_API_KEY + k.Client_REQ_TOKEN + k.Client_API_SECRET
	hasher.Write([]byte(checksum))
	checksum = hex.EncodeToString(hasher.Sum(nil))
	//Create Http client, add the required fields
	hc := httpClient(DEFAULT_TIMEOUT)
	form := url.Values{}
	form.Add("api_key", k.Client_API_KEY)
	form.Add("request_token", k.Client_REQ_TOKEN)
	form.Add("checksum", checksum)
	//Create the request
	req, err := http.NewRequest(POST, API_ROOT+TOKEN_URL, strings.NewReader(form.Encode()))
	helper.CheckError(err)

	//Do the request
	resp, err := hc.Do(req)
	helper.CheckError(err, resp)

	//Read the response
	message, err := (ioutil.ReadAll(resp.Body))
	helper.CheckError(err)

	//parse accesstoken and store
	accToken, _, _, err := jsonparser.Get(message, "data", "access_token")
	helper.CheckError(err)
	k.SetAccessToken(string(accToken))
	if k.Client_ACC_TOKEN != "" {

		fmt.Println("Access Key set")
	}

	//parse publictoken and store
	pubToken, _, _, err := jsonparser.Get(message, "data", "public_token")
	helper.CheckError(err)
	k.SetPublicToken(string(pubToken))
	if k.Client_PUB_TOKEN != "" {
		fmt.Println("Public Key set")
	}

}

//dates of format yyyy-mm-dd
//concurrent safe as long as a million copies are not called, I THINK
func (k *kiteClient) GetHistorical(duration string, exchangeToken string, from string, to string, filename string) {
	//Create HTTP client
	hc := httpClient(30)
	//Create basic request
	//If duration is day then we can just grab the entire interval at once
	if duration == DAY {

		req, err := http.NewRequest(GET, API_ROOT+HISTORICAL+exchangeToken+"/"+duration, nil)
		helper.CheckError(err)
		//Add parameters to request
		form := req.URL.Query()
		form.Add("api_key", k.Client_API_KEY)
		form.Add("access_token", k.Client_ACC_TOKEN)
		form.Add("from", from)
		form.Add("to", to)
		req.URL.RawQuery = form.Encode()
		//Create new request with parameters
		req, err = http.NewRequest(GET, req.URL.String(), nil)
		helper.CheckError(err)
		//Get the historical data
		resp, err := hc.Do(req)
		helper.CheckError(err, resp)

		//Read it
		message, err := ioutil.ReadAll(resp.Body)
		helper.CheckError(err)
		//	fmt.Println(string(message))
		//Parse to get Candles
		data, _, _, err := jsonparser.Get(message, "data", "candles")
		helper.CheckError(err)

		//Format correctly
		data = helper.FormatData(string(data))

		//Store
		err = ioutil.WriteFile(filename, data, 0644)
		helper.CheckError(err)
	} else { //if Duration is not day then we need to split it into multiple days
		dataFile, _ := os.OpenFile(filename,
			os.O_WRONLY|os.O_CREATE, 0666)
		curr, _ := time.Parse(DEFAULT_DATE_LAYOUT, from)
		final, _ := time.Parse(DEFAULT_DATE_LAYOUT, to)
		// start is i, increment is i to i + 30 days, stop when the difference between final and now is less than 28
		for curr = curr.Add(-1 * 24 * time.Hour); final.Sub(curr) > 24*29*time.Hour; curr = curr.Add(24 * 29 * time.Hour) {
			curr = curr.Add(24 * time.Hour)
			req, err := http.NewRequest(GET, API_ROOT+HISTORICAL+exchangeToken+"/"+duration, nil)
			helper.CheckError(err)
			//Add parameters to request
			form := req.URL.Query()
			form.Add("api_key", k.Client_API_KEY)
			form.Add("access_token", k.Client_ACC_TOKEN)
			form.Add("from", curr.Format(DEFAULT_DATE_LAYOUT))
			form.Add("to", (curr.Add(29 * 24 * time.Hour)).Format(DEFAULT_DATE_LAYOUT))
			req.URL.RawQuery = form.Encode()
			fmt.Println(req.URL.String())
			req, err = http.NewRequest(GET, req.URL.String(), nil)
			helper.CheckError(err)
			//Get the historical data
			resp, err := hc.Do(req)
			time.Sleep(1 * time.Second)
			helper.CheckError(err, resp)
			message, err := ioutil.ReadAll(resp.Body)
			helper.CheckError(err)
			//	fmt.Println(string(message))
			//Parse to get Candles
			data, _, _, err := jsonparser.Get(message, "data", "candles")
			helper.CheckError(err)
			data = helper.FormatData(string(data))
			_, err = dataFile.Write(data)
			_, err = dataFile.Write([]byte("\n"))
			helper.CheckError(err)
			fmt.Println("Looped")

		}
		//repeat for last remaining bit
		req, err := http.NewRequest(GET, API_ROOT+HISTORICAL+exchangeToken+"/"+duration, nil)
		helper.CheckError(err)
		form := req.URL.Query()
		form.Add("api_key", k.Client_API_KEY)
		form.Add("access_token", k.Client_ACC_TOKEN)
		form.Add("from", curr.Format(DEFAULT_DATE_LAYOUT))
		form.Add("to", final.Format(DEFAULT_DATE_LAYOUT))
		req.URL.RawQuery = form.Encode()
		fmt.Println(req.URL.String())
		req, err = http.NewRequest(GET, req.URL.String(), nil)
		helper.CheckError(err)
		//Get the historical data
		resp, err := hc.Do(req)
		helper.CheckError(err, resp)
		message, err := ioutil.ReadAll(resp.Body)
		helper.CheckError(err)
		//	fmt.Println(string(message))
		//Parse to get Candles
		data, _, _, err := jsonparser.Get(message, "data", "candles")
		helper.CheckError(err)
		data = helper.FormatData(string(data))
		_, err = dataFile.Write(data)
		helper.CheckError(err)
		dataFile.Close()
		//fmt.Println("Finished with ", exchangeToken)

	}

}
