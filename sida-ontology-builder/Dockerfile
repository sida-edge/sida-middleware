FROM golang:alpine AS builder

RUN apk add --no-cache gcc musl-dev pkgconfig zeromq-dev

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=1 GOOS=linux go build -ldflags="-s -w" -o ontology-builder cmd/server/main.go

##
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata zeromq

WORKDIR /app

COPY --from=builder /app/ontology-builder .

ENV NEO4J_URI="neo4j://neo4j:7687"
ENV NEO4J_USERNAME="neo4j"
ENV NEO4J_PASSWORD="sida_password"
ENV ZMQ_ENDPOINT="tcp://sida-core:5556"

CMD ["./ontology-builder"]