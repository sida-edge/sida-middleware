FROM golang:1.26.4-alpine AS builder    

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o sida-memory-worker main.go

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/sida-memory-worker .

CMD ["./sida-memory-worker"]