{{/*
Expand the name of the chart.
*/}}
{{- define "zscaler-mcp-server.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to
this (by the DNS naming spec).
*/}}
{{- define "zscaler-mcp-server.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "zscaler-mcp-server.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels (applied to every object in the release).
*/}}
{{- define "zscaler-mcp-server.labels" -}}
helm.sh/chart: {{ include "zscaler-mcp-server.chart" . }}
{{ include "zscaler-mcp-server.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: zscaler-mcp
{{- end -}}

{{/*
Selector labels (must remain immutable across upgrades).
*/}}
{{- define "zscaler-mcp-server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "zscaler-mcp-server.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Image reference: prefer digest if set, otherwise tag. Defaults to
`latest` if both tag and digest are blank (matches what Docker Hub
actually publishes).
*/}}
{{- define "zscaler-mcp-server.image" -}}
{{- $repo := .Values.image.repository -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" $repo .Values.image.digest -}}
{{- else -}}
{{- $tag := default "latest" .Values.image.tag -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end -}}

{{/*
ServiceAccount name to use.
*/}}
{{- define "zscaler-mcp-server.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "zscaler-mcp-server.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Name of the Secret holding OneAPI credentials. Returns the chart-managed
name when secret.create is true, otherwise the operator-supplied
existingName. Pre-validated by validateValues so we never return empty.
*/}}
{{- define "zscaler-mcp-server.secretName" -}}
{{- if .Values.secret.create -}}
{{- printf "%s-creds" (include "zscaler-mcp-server.fullname" .) -}}
{{- else -}}
{{- .Values.secret.existingName -}}
{{- end -}}
{{- end -}}

{{/*
Mutual-exclusion + sanity validation. Called from the Deployment template
so any helm install / helm template surfaces the message before kubectl
ever sees an invalid manifest.

This deliberately fails-fast for the four most common configuration
mistakes:
  - ingress.enabled AND httproute.enabled at the same time
  - secret.create false AND secret.existingName empty
  - secret.create true AND every value blank (probably forgotten)
  - auth.mode invalid value
*/}}
{{- define "zscaler-mcp-server.validateValues" -}}
{{- if and .Values.ingress.enabled .Values.httproute.enabled -}}
{{- fail "ingress.enabled and httproute.enabled are mutually exclusive — pick exactly one." -}}
{{- end -}}
{{- if and (not .Values.secret.create) (eq (toString .Values.secret.existingName) "") -}}
{{- fail "secret.create is false but secret.existingName is empty — either let the chart create the Secret or point at an existing one." -}}
{{- end -}}
{{- if .Values.secret.create -}}
{{- $v := .Values.secret.values -}}
{{- if and (eq (toString $v.clientId) "") (eq (toString $v.clientSecret) "") (eq (toString $v.privateKey) "") -}}
{{- fail "secret.create is true but secret.values.clientId / clientSecret / privateKey are all empty — chart would render an empty credentials Secret." -}}
{{- end -}}
{{- end -}}
{{- $modes := list "jwt" "api-key" "zscaler" "none" -}}
{{- if not (has .Values.mcp.auth.mode $modes) -}}
{{- fail (printf "mcp.auth.mode %q is invalid — must be one of: jwt, api-key, zscaler, none" .Values.mcp.auth.mode) -}}
{{- end -}}
{{- end -}}
