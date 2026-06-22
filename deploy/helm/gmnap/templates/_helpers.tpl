{{/* Common labels — keeps every resource consistently tagged. */}}
{{- define "gmnap.labels" -}}
app.kubernetes.io/name: gmnap
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "gmnap.apiSelectorLabels" -}}
app.kubernetes.io/name: gmnap-api
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "gmnap.memgraphSelectorLabels" -}}
app.kubernetes.io/name: memgraph
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
