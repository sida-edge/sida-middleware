FROM golang:alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o worker main.go

FROM alpine:latest

WORKDIR /app
RUN apk --no-cache add ca-certificates tzdata

COPY --from=builder /app/worker .

CMD ["./worker"]