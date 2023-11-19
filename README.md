# multi_armed_bandit_service
Simple pet project

Build docker images
```shell
make build
```

Extract data from tar
```shell
make prepare-data
```

Start service
```shell
make run
```

Check liveness: open [0.0.0.0:8090](http://0.0.0.0:8090/) in your browser


Check user interface: open [0.0.0.0:8501](http://0.0.0.0:8501/) in your browser


Start jupyter (if you want to do some EDA) and check interface [0.0.0.0:8888](http://0.0.0.0:8888/) in your browser
```shell
make run-jupyter
```
