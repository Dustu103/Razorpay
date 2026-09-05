FROM golang:1.23.0-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o dropoff-service ./cmd/server/main.go

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/dropoff-service .

EXPOSE 3002
CMD ["./dropoff-service"]
