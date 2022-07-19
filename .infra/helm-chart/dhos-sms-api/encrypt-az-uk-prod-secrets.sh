#!/bin/bash

## ensure we have the necessary whitelist set to access the keyvault in azure (https://portal.azure.com/#@sensynehealth.com/resource/subscriptions/63ad258a-0f7e-4336-8e52-52f29e5e4dd2/resourceGroups/ukprod/providers/Microsoft.KeyVault/vaults/uk-prod-keyvault/networking)
echo Encrypting prod secrets file
sops --encrypt values-az-uk-prod006-secrets.yaml > values-az-uk-prod006-secrets-sops.yaml
