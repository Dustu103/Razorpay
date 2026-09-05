FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod ./
RUN go mod tidy || true

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o nach-recovery-service ./cmd/server/main.go

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/nach-recovery-service .

EXPOSE 3007
CMD ["./nach-recovery-service"]
