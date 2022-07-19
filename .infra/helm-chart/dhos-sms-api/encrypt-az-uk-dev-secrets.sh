#!/bin/bash

echo Encrypting dev secrets file

sops --encrypt values-az-uk-dev-secrets.yaml > values-az-uk-dev-secrets-sops.yaml
