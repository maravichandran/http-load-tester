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
docker run http-load-tester http://example.com
```

To run the container with custom arguments:
```bash
docker run http-load-tester http://example.com --qps 20 --duration 5
```

An example output of the above command is below:
```txt
Results for http://example.com
Total requests: 100
Total errors: 0
Error rate: 0.000%
Mean latency: 47.345 milliseconds
Median latency: 41.492 milliseconds
Min latency: 15.457 milliseconds
Max latency: 121.339 milliseconds

Status code distribution:
  200: 100
```

### Automatically finding the breaking point of the server
If you'd like to find the highest qps (queries per second) that the server can handle without exceeding the acceptable levels of mean latency and error rate, you can use the following command. The program will do a binary search on all levels of qps between 0 and the max qps provided to find the highest tolerable qps.

You can change the url, duration, max qps, max error rate, and max latency as needed. 
```bash
 docker run http-load-tester http://apple.com --find-breaking-point --duration=8 --max-qps 1000 --max-error-rate 0.01 --max-latency 0.5
```

An example output of this command is:
```txt
Beginning search for breaking point.
Tested QPS: 500, Error Rate: 0.00%, Mean Latency: 3.517s
Tested QPS: 250, Error Rate: 0.00%, Mean Latency: 1.974s
Tested QPS: 125, Error Rate: 0.00%, Mean Latency: 1.188s
Tested QPS: 62, Error Rate: 0.00%, Mean Latency: 0.703s
Tested QPS: 31, Error Rate: 0.00%, Mean Latency: 0.372s
Tested QPS: 46, Error Rate: 0.00%, Mean Latency: 0.496s
Tested QPS: 54, Error Rate: 0.00%, Mean Latency: 0.602s
Tested QPS: 50, Error Rate: 0.00%, Mean Latency: 0.577s
Tested QPS: 48, Error Rate: 0.00%, Mean Latency: 0.536s
Tested QPS: 47, Error Rate: 0.00%, Mean Latency: 0.521s

Breaking point found: 46 QPS

Final test results:
Results for http://apple.com
Total requests: 368
Total errors: 0
Error rate: 0.000%
Mean latency: 476.503 milliseconds
Median latency: 449.405 milliseconds
Min latency: 180.404 milliseconds
Max latency: 1268.814 milliseconds

Status code distribution:
  200: 368
```

## CLI documentation
The documentation for the CLI is below. 
```txt
usage: load_tester.py [-h] [--qps QPS] [--duration DURATION]
                      [--find-breaking-point] [--max-qps MAX_QPS]
                      [--max-error-rate MAX_ERROR_RATE]
                      [--max-latency MAX_LATENCY]
                      url

HTTP Load Testing Tool

positional arguments:
  url                   Target URL to test

optional arguments:
  -h, --help            show this help message and exit
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
```