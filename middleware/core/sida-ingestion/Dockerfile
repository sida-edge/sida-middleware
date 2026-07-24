FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential cmake pkg-config \
    libzmq3-dev nlohmann-json3-dev \
    libcurl4-openssl-dev \
    libmodbus-dev git python3 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone -b v1.3.6 https://github.com/open62541/open62541.git /tmp/open62541 && \
    cd /tmp/open62541 && mkdir build && cd build && \
    cmake -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc) && make install && ldconfig

WORKDIR /app

COPY CMakeLists.txt .
COPY core/ core/
COPY drivers/ drivers/
COPY main.cpp .

RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc)

# 
FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libzmq5 libcurl4 libmodbus5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=builder /usr/local/lib/libopen62541.so* /usr/local/lib/

RUN ldconfig

COPY --from=builder /app/build/ingestion_service /app/ingestion_service

CMD ["./ingestion_service"]