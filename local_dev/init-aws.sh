#!/bin/bash
awslocal sqs create-queue --queue-name game-queue
awslocal sqs create-queue --queue-name game-analysis-queue
