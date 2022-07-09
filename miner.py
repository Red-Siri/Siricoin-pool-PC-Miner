import os, sys, time, sha3, requests, json, random
from rich import print


siriAddress = "0xc79878fCD826EC7e00c9cB754f8242F3466dead5"
poolURL = "http://168.138.151.204/poolsiri/"

hashes_per_list = 1024
hashrateRefreshRate = 25 # Secconds
restartTime = 30 # Secconds


def main():
    id = pool.login()
    console_log.logged_in(id)
    
    startTime = time.time()
    hashrates = []
    
    while True:
        job = pool.requestJob(id)
        bRoot = beaconRoot(job["lastBlockHash"], job["timestamp"], job["PoolAddr"])
        FinalHash = PoW(bRoot, job["startNonce"], job["EndNonce"], job["target"])
    
        if not FinalHash[0]:
            hashrates.append(FinalHash[1]["Hashrate"])
            time.sleep(random.randint(1, 3))
            console_log.share("Share", pool.submit(id, job["JOB_ID"], "0x00", job["timestamp"], 1))
    
        if FinalHash[0]:
            hashrates.append(FinalHash[1]["Hashrate"])
            console_log.rgbPrint("Block found, submiting to pool", "magenta")
            time.sleep(random.randint(1, 3))
            console_log.share("Block", pool.submit(id, job["JOB_ID"], FinalHash[1]["Proof"], job["timestamp"], FinalHash[1]["Nonce"]))
    
        if time.time() - startTime > hashrateRefreshRate:   
            console_log.hashrate(hashrates)
            hashrates = []
            startTime = time.time()  
    
        time.sleep(random.randint(2, 5))


def Restart():
    console_log.rgbPrint("Pool refused connection, trying again in " + str(restartTime) + "s", "red")
    time.sleep(restartTime)
    os.execl(sys.executable, sys.executable, *sys.argv)


def formatHashrate(hashrate):
    if hashrate < 1000:
        return f"{round(hashrate, 2)} H/s"
    elif hashrate < 1000000:
        return f"{round(hashrate/1000, 2)} kH/s"
    elif hashrate < 1000000000:
        return f"{round(hashrate/1000000, 2)} MH/s"
    elif hashrate < 1000000000000:
        return f"{round(hashrate/1000000000, 2)} GH/s"

class pool:

    def login():
        try:
            return requests.post(poolURL, json={'id': None, 'method': 'mining.authorize', 'params': [siriAddress]}).json()["id"]

        except (requests.ConnectionError, requests.ConnectTimeout, requests.HTTPError, requests.JSONDecodeError, requests.ReadTimeout, requests.Timeout, requests.TooManyRedirects, requests.RequestException): Restart()

    def requestJob(id):
        try:
            response = requests.post(poolURL, json={'id': id, 'method': 'mining.subscribe', 'params': ['PC']}).json()["params"]

        except (requests.ConnectionError, requests.ConnectTimeout, requests.HTTPError, requests.JSONDecodeError, requests.ReadTimeout, requests.Timeout, requests.TooManyRedirects, requests.RequestException): Restart()

        return {"JOB_ID": response[0], "lastBlockHash": response[1], "target": response[2], "startNonce": response[3], "EndNonce": response[4], "timestamp": response[7], "PoolAddr": response[9]}

    def submit(id, jobID, proof, timestamp, nonce):
        try:
            response = requests.post(poolURL, json={"id": id, "method": "mining.submit", "params": [siriAddress, jobID, proof, timestamp, nonce]}).json()

        except (requests.ConnectionError, requests.ConnectTimeout, requests.HTTPError, requests.JSONDecodeError, requests.ReadTimeout, requests.Timeout, requests.TooManyRedirects, requests.RequestException): Restart()

        if response["result"]:
            if not response["raw"] == False:
                # Share accepted with TXID
                return {"Accepted": True, "TXID": json.loads(response["raw"])["result"][0]}
            else:
                # Share accepted, but no TXID
                return {"Accepted": True, "TXID": False}
        else:
            # Share rejected
            return {"Accepted": False, "TXID": False}

class console_log:

    def rgbPrint(string, color):
        print("[" + color + "]" + str(string) + "[/" + color + "]")
    
    def logged_in(id):
        console_log.rgbPrint("Logged in as: " + siriAddress + "@" + poolURL + ", ID: " + str(id), "cyan")

    def share(type, data):
        if data["Accepted"]:
            if data["TXID"]:
                console_log.rgbPrint(type + " accepted, TXID: " + json.loads(data["TXID"])["result"][0], "green")
            else:
                console_log.rgbPrint(type + " accepted, pool dry", "yellow")
        else:
            console_log.rgbPrint(type + " rejected", "red")
    
    def hashrate(hashrates):
        console_log.rgbPrint("Hashrate: " + formatHashrate(sum(hashrates)/len(hashrates)), "cyan")



def beaconRoot(lastBlockHash, timestamp, poolAddr):
    messagesHash = b'\xef\xbd\xe2\xc3\xae\xe2\x04\xa6\x9bv\x96\xd4\xb1\x0f\xf3\x117\xfex\xe3\x94c\x06(O\x80n-\xfch\xb8\x05' # Messages hash is constant, no need to hash it everytime
    bRoot = sha3.keccak_256(bytes.fromhex(lastBlockHash.replace("0x", "")) + int(timestamp).to_bytes(32, 'big') + messagesHash + bytes.fromhex(poolAddr.replace("0x", ""))).digest()
    return bRoot


def PoW(bRoot, start_nonce, end_nonce, target):   
    target = int(target, 16) 
    nonce = start_nonce

    bRoot_hashed = sha3.keccak_256(bRoot)
    bRoot_hashed.update((0).to_bytes(24, "big"))

 
    start = time.time()
    hashes = []

    while True:

        for i in range (hashes_per_list):
            finalHash = bRoot_hashed.copy()
            finalHash.update(nonce.to_bytes(32, "big"))
            hashes.append(finalHash)
            nonce +=1

        for hash in hashes:
            if (int.from_bytes(hash.digest(), "big") < target):
                validNonce = (nonce - (len(hashes) - hashes.index(hash)))
                return True, {"Nonce": validNonce, "Proof": "0x" + hash.hexdigest(), "Hashrate": (nonce - start_nonce) / (time.time() - start)}

        if nonce > end_nonce:
            return False, {"Hashrate": (nonce - start_nonce) / (time.time() - start)}

        hashes = []

main()
