FROM golang:1.23.0-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o b2b-server ./cmd/server

FROM alpine:latest

RUN apk add --no-cache wget

WORKDIR /app

COPY --from=builder /app/b2b-server .

CMD ["./b2b-server"]
