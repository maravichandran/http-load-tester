# HTTP Load Tester
HTTP Load Tester written in Python

- [HTTP Load Tester](#http-load-tester)
  - [Usage](#usage)
    - [Running a single load test](#running-a-single-load-test)
    - [Automatically finding the breaking point of the server](#automatically-finding-the-breaking-point-of-the-server)
  - [CLI documentation](#cli-documentation)

## Usage
To build the Docker image:
```bash
docker build -t http-load-tester .
```

Please note that the unit of time for all below terminal commands is seconds. 

### Running a single load test
To run the container with default arguments (`qps=20`, `duration=5`):
```bash
docker run http-load-tester --url http://example.com
```

To run the container with custom arguments:
```bash
docker run http-load-tester --url http://example.com --qps 5 --duration 5
```

An example output of the above command is below:
```txt
Results for http://example.com
Total requests: 25
Total errors: 0
Error rate: 0.000%
Mean latency: 18.347 milliseconds
Median latency: 17.637 milliseconds
Min latency: 11.618 milliseconds
Max latency: 40.071 milliseconds

Status code distribution:
  200: 25
```

### Automatically finding the breaking point of the server
If you'd like to find the highest qps (queries per second) that the server can handle without exceeding the acceptable levels of mean latency and error rate, you can use the following command. The program will do a binary search on all levels of qps between 0 and the max qps provided to find the highest tolerable qps.

You can change the url, duration, max qps, max error rate, and max latency as needed. 
```bash
docker run http-load-tester --url http://192.168.111.28:8000 --find-breaking-point --duration=5 --max-qps 1000 --max-error-rate 0.01 --max-latency 0.5
```

An example output of this command is:
```txt
Beginning search for breaking point.
Tested QPS: 500, Error Rate: 0.12%, Mean Latency: 0.026s
Tested QPS: 750, Error Rate: 0.16%, Mean Latency: 0.033s
Tested QPS: 875, Error Rate: 0.11%, Mean Latency: 0.027s
Tested QPS: 938, Error Rate: 0.15%, Mean Latency: 0.042s
Tested QPS: 969, Error Rate: 0.14%, Mean Latency: 0.030s
Tested QPS: 985, Error Rate: 0.14%, Mean Latency: 0.035s
Tested QPS: 993, Error Rate: 0.10%, Mean Latency: 0.040s
Tested QPS: 997, Error Rate: 0.12%, Mean Latency: 0.028s
Tested QPS: 999, Error Rate: 0.12%, Mean Latency: 0.030s
Tested QPS: 1000, Error Rate: 0.32%, Mean Latency: 0.073s

Breaking point not found within range. The server had adequate performance at all levels of queries per second tested.

Final test results:
Results for http://192.168.111.28:8000
Total requests: 5000
Total errors: 7
Error rate: 0.140%
Mean latency: 31.362 milliseconds
Median latency: 7.566 milliseconds
Min latency: 4.511 milliseconds
Max latency: 15017.129 milliseconds

Status code distribution:
  200: 4993
  error: 7
```

## CLI documentation
The documentation for the CLI is below. 
```txt

usage: load_tester.py [-h] [--url URL] [--qps QPS] [--duration DURATION]
                      [--find-breaking-point] [--max-qps MAX_QPS]
                      [--max-error-rate MAX_ERROR_RATE]
                      [--max-latency MAX_LATENCY] [--verbose]
                      [--retries RETRIES]

HTTP Load Testing Tool

optional arguments:
  -h, --help            show this help message and exit
  --url URL             Target URL to test
  --qps QPS             Queries per second for a single test
  --duration DURATION   Test duration in seconds
  --find-breaking-point
                        Find the breaking point of the server
  --max-qps MAX_QPS     Maximum queries per second to test when finding
                        breaking point
  --max-error-rate MAX_ERROR_RATE
                        Maximum acceptable error rate when finding breaking
                        point
  --max-latency MAX_LATENCY
                        Maximum acceptable mean latency in seconds when
                        finding breaking point
  --verbose             Print verbose output including error messages
  --retries RETRIES     Number of retry attempts for a failed request

```