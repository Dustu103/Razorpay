FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o nach-recovery-service ./cmd/server/main.go

FROM alpine:3.19
RUN apk add --no-cache wget
WORKDIR /app
COPY --from=builder /app/nach-recovery-service .

EXPOSE 3007
CMD ["./nach-recovery-service"]
