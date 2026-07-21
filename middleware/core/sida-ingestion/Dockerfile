FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libmodbus-dev \
    libzmq3-dev \
    nlohmann-json3-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

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
    libzmq5 \
    libmodbus5 \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=builder /app/build/ingestion_service /app/ingestion_service

CMD ["./ingestion_service"]