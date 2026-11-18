# KCNA Questions Assessment — Manual In-Session Review

**Reviewer**: Claude (manual, no API calls)
**Questions assessed**: kcna-001 through kcna-230 (230 total)
**Date**: 2026-05-28

---

## Summary Counts

| Status | Count |
|---|---|
| correct | 199 |
| fix_needed | 22 |
| questionable | 9 |

---

## fix_needed Issues

### kcna-019
- **Wrong answer**: C (External)
- **Correct answer**: D (Pods)
- **Reason**: The question asks about scaling based on "custom application metrics." The `Pods` metric type in HPA v2 is explicitly designed for custom per-pod application metrics (e.g., requests per second per pod). `External` is for metrics sourced from *outside* the cluster (e.g., cloud queue length). The explanation incorrectly states "Pods is not a valid metric type for HPA" — `Pods` IS a valid HPA v2 metric type (`.spec.metrics[].type: Pods`).

### kcna-024
- **Wrong answer**: D (sessionAffinity)
- **Correct answer**: A (type: ClusterIP)
- **Reason**: The question asks "which field determines whether the Service gets a stable virtual IP?" A ClusterIP type service gets a stable virtual IP allocated. `sessionAffinity` controls client-IP stickiness for routing, has nothing to do with whether a stable virtual IP is allocated. The explanation for D is incoherent and self-contradictory.

### kcna-028
- **Wrong answer**: D (ResourceQuota)
- **Correct answer**: C (PodSecurityPolicy)
- **Reason**: The question asks which is NOT a built-in admission controller. ResourceQuota IS a built-in admission controller (enabled by default in Kubernetes) that enforces namespace-level resource limits at admission time. PodSecurityPolicy was a built-in admission controller that was deprecated in v1.21 and removed in v1.25. For a current Kubernetes context, PodSecurityPolicy is removed and thus no longer "built-in," making C the better answer. Alternatively, if the set includes current k8s, both ResourceQuota (still present) and NodeRestriction (B) and NamespaceLifecycle (A) are built-in, and PSP (C) is removed. Answer should be C.

### kcna-073
- **Wrong answer**: B (scheduler.kubernetes.io/name annotation)
- **Correct answer**: The correct way to set a custom scheduler for a Pod is via the `spec.schedulerName` field in the Pod spec, not an annotation. None of the annotation options listed are the standard current approach. The question is misleading. If forced to pick from the options, none are fully correct, but the question should reference `spec.schedulerName`. Mark as fix_needed — question should be rewritten to ask about `spec.schedulerName`.

### kcna-110
- **Wrong answer**: B (preStop)
- **Reason**: The question asks "which field runs AFTER the container exits?" Neither answer B (preStop) nor any other option is correct. `preStop` runs BEFORE the container is terminated, not after. `postStart` runs after the container starts. There is no lifecycle hook that runs after the container exits. The question itself is based on a false premise. The question should be corrected — if asking about "just before container exits," the answer is preStop. But asking about "after the container exits" has no correct Kubernetes answer. Recommend rewriting the question to ask about preStop correctly.

### kcna-121
- **Current answer**: C (service.beta.kubernetes.io/aws-load-balancer-scheme: internal)
- **Correct answer**: A (service.beta.kubernetes.io/aws-load-balancer-internal: "true")
- **Reason**: The traditional and most widely documented annotation for requesting an internal AWS ELB is `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` (option A). Option C (`aws-load-balancer-scheme: internal`) is valid only for the newer AWS Load Balancer Controller v2+ NLB/ALB, not for the classic in-tree provider. For the KCNA exam context, option A is the better-known annotation.

### kcna-127
- **Wrong answer**: B
- **Reason**: The question asks what `--record` does. Both options A and B say the annotation is `kubectl.kubernetes.io/last-applied-configuration`, which is wrong. The `--record` flag stores the command in the `kubernetes.io/change-cause` annotation (visible in rollout history). Also, `--record` is deprecated in recent Kubernetes versions. The answer and explanation reference the wrong annotation name. Answer should be corrected to note the `kubernetes.io/change-cause` annotation.

### kcna-128
- **Wrong answer**: B (portProtocol)
- **Correct answer**: A (protocol)
- **Reason**: The explanation for this question explicitly states "Answer B: 'portProtocol' is not a valid field; the correct field is 'protocol'. A: 'protocol' is the correct field; this option is a distractor." The explanation acknowledges A is correct but the `answer` field says B. This is a clear data entry error — the answer field must be changed to A.

### kcna-130
- **Wrong answer**: C (consul.io/inject: "yes")
- **Correct answer**: A (consul.hashicorp.com/connect-inject: "true")
- **Reason**: The correct Consul Connect sidecar injection annotation is `consul.hashicorp.com/connect-inject: "true"`. Option C (`consul.io/inject: "yes"`) does not exist in Consul documentation. The explanation incorrectly states C is correct.

### kcna-131
- **Wrong answer**: D (The pod will restart immediately)
- **Correct answer**: A (The Service will route traffic to all pods with that label)
- **Reason**: The question asks about the effect of adding the label 'tier=backend' to a pod and creating a Service with that selector. The correct effect is that the Service routes traffic to matching pods (option A). Option D is the "trick" answer designed to be wrong. The answer field is set to D, which is the wrong option. The explanation even contradicts itself: "Answer D: Adding a label does not trigger a pod restart. A: Correct behavior is routing traffic, not deletion."

### kcna-132
- **Wrong answer**: D (persistentVolumeReclaimPolicy)
- **Correct answer**: B (accessModes)
- **Reason**: The question asks "which field in a PersistentVolume determines whether the volume can be mounted as read-only?" The correct answer is `accessModes` — e.g., ReadOnlyMany (ROX) or ReadWriteOnce constrain mounting semantics. `persistentVolumeReclaimPolicy` controls what happens after the PVC is released (Retain, Recycle, Delete), not mount mode.

### kcna-133
- **Wrong answer**: D (The time the Deployment controller waits before scaling)
- **Correct answer**: A (The minimum time a pod must be ready before it is considered available)
- **Reason**: The question asks what `spec.minReadySeconds` controls. Option A correctly describes the field: a pod is considered available only after it has been running without crashing for at least `minReadySeconds`. The explanation contradicts itself, stating "Answer D: minReadySeconds does not affect scaling delays. A: That describes minReadySeconds correctly; this option is actually the correct definition." The answer field must be changed to A.

### kcna-134
- **Wrong answer**: D (DaemonSet)
- **Correct answer**: A (Headless Service)
- **Reason**: The question asks "which Kubernetes object provides a stable network identity for each pod in a StatefulSet?" The answer is a Headless Service (clusterIP: None) combined with the StatefulSet's `serviceName` field, which gives each pod a predictable DNS name like `pod-0.service.namespace.svc.cluster.local`. DaemonSet has nothing to do with network identity in StatefulSets.

### kcna-135
- **Wrong answer**: C (Specify node affinity for Job Pods)
- **More accurate answer**: A (Select which Pods the Job should manage) or D (Jobs do not have a selector field — as kcna-144 correctly states)
- **Reason**: This is inconsistent with kcna-144 which asks the same question and correctly answers D (Jobs do not have a selector field). Both questions cannot be correct simultaneously. Recommend making kcna-135 match kcna-144 with answer D.

### kcna-136
- **Wrong answer**: D (loadBalancerSourceRanges)
- **Correct answer**: A (sessionAffinity: ClientIP)
- **Reason**: The question asks "which field enables session affinity based on client IP?" The correct answer is clearly `sessionAffinity: ClientIP` (option A). `loadBalancerSourceRanges` restricts which external IPs can access a LoadBalancer service. The explanation even states "A: This is the correct way to enable client IP affinity; the option is a distractor."

### kcna-137
- **Wrong answer**: B (full YAML manifest)
- **Correct answer**: A (cluster IP, external IPs, and ports)
- **Reason**: `kubectl get svc -o wide` adds extra columns (like SELECTOR) compared to plain `kubectl get svc`. It does NOT return the full YAML manifest (that requires `-o yaml`). The explanation contradicts the answer, stating "-o wide adds additional columns such as external IPs and ports, not the full YAML."

### kcna-147
- **Wrong answer**: D (linkerd.io/inject: "true")
- **Correct answer**: A (linkerd.io/inject: "enabled")
- **Reason**: Linkerd documentation consistently specifies `linkerd.io/inject: "enabled"` as the annotation value for sidecar injection. The value "true" is not documented as valid. This conflicts with kcna-104 and kcna-112 which both correctly use "enabled." Within this same question set, three questions (104, 112, 147) ask about the same Linkerd annotation — 104 and 112 correctly use "enabled," while 147 incorrectly uses "true."

### kcna-201
- **Wrong answer**: D (123test)
- **Correct answer**: This question is likely incorrect
- **Reason**: Kubernetes namespace names follow RFC 1123 DNS label rules, which DO allow names starting with digits. "123test" is a valid DNS label and a valid Kubernetes namespace name. The claim that it is invalid because it "cannot start with a digit" is incorrect for RFC 1123. The question may need to be rewritten with an actually invalid namespace name (e.g., one containing uppercase letters or special characters like `My_App`).

### kcna-209
- **Wrong answer**: B (v1.12)
- **Correct answer**: A (v1.9)
- **Reason**: The Deployment resource was promoted to the stable `apps/v1` API in Kubernetes v1.9. It was in `apps/v1beta1` in v1.6 and `apps/v1beta2` in v1.8. The GA stable `apps/v1` version appeared in v1.9, not v1.12.

### kcna-214
- **Wrong answer**: D (Want to use a static external IP address)
- **Correct answer**: B (Cloud provider does not support external load balancers)
- **Reason**: The question asks when to prefer NodePort over LoadBalancer. Using a static external IP is not a reason to prefer NodePort — LoadBalancer services also support static IPs via `loadBalancerIP`. The correct reason to use NodePort is when there is no cloud provider load balancer available (option B).

### kcna-223
- **Wrong answer**: B (ExternalMetric)
- **Correct answer**: D (HorizontalPodAutoscaler)
- **Reason**: "ExternalMetric" is not a standard Kubernetes API resource object. HPA v2 consumes external metrics via the `external.metrics.k8s.io` API, but there is no standalone Kubernetes object named "ExternalMetric." The HPA itself is the resource that references external metrics in its spec. This question is poorly worded — none of the other options are correct either. The HPA (D) is the object that enables custom metric autoscaling. However, the question should probably be rewritten entirely.

### kcna-224
- **Wrong answer**: C (networking.gke.io/load-balancer-type: "External")
- **Correct answer**: B (cloud.google.com/backend-config with HTTP2 protocol)
- **Reason**: To enable HTTP/2 for a GKE LoadBalancer backend, the correct approach is using a BackendConfig resource referenced via the `cloud.google.com/backend-config` annotation with `{"protocol":"HTTP2"}` (option B). The `networking.gke.io/load-balancer-type` annotation controls whether the load balancer is Internal or External, not HTTP/2 support.

---

## questionable Questions

### kcna-005
The answer A (envFrom) is the most complete way to use a ConfigMap as environment variables, but option B (configMapKeyRef) is also used within `env[].valueFrom` to reference a ConfigMap key as an env var. The question wording "which key is used" is somewhat ambiguous. Both A and envFrom/configMapKeyRef are valid approaches. Defensible but imprecise.

### kcna-014
Answer B (ClusterRole). The question asks "which object grants permissions to a group of users or service accounts?" Both Role and ClusterRole can grant permissions; the difference is scope. ClusterRole is correct for cluster-wide, but Role is also used for namespace-scoped grants. The question lacks the "cluster-wide" qualifier but B is defensible.

### kcna-040
Answer B (kubectl port-forward) is marked as "expose a pod directly without a Service." port-forward is a local debugging tool and is not a proper exposure mechanism for production. Option C (hostPort) actually does expose a pod directly on the node's IP without a Service, which is a more accurate interpretation of "exposing without a Service." Both are debatable.

### kcna-053
Answer B (PodSecurityPolicy). PodSecurityPolicy is deprecated (v1.21) and removed (v1.25). For modern Kubernetes, the equivalent is Pod Security Admission (PodSecurity admission controller) or OPA/Gatekeeper. The answer is technically correct for older Kubernetes but questionable for current versions.

### kcna-089
Answer D ("none – keep-alive is handled by the underlying socket implementation"). While this is true that Kubernetes has no explicit keep-alive setting in Service spec, `sessionAffinityConfig.clientIP.timeoutSeconds` (option B path) is a related configurable field in Service that does exist. The question and answer are defensible but imprecise.

### kcna-113
Answer B states "Operator Exists matches any key; with NoExecute the pod is evicted after the specified tolerationSeconds (or immediately if omitted)." This is partially accurate but option A also has truth to it. If `tolerationSeconds` is NOT specified with `operator: Exists` and `effect: NoExecute`, the pod is NOT evicted (it can stay indefinitely). Option A states the pod "will not be evicted when the taint is added" — which is true when no `tolerationSeconds` is set. The question is ambiguous about whether `tolerationSeconds` is set.

### kcna-196
Answer B (--header). This is a question about NGINX Ingress controller CLI flags. The `--header` flag is not a well-documented, standard NGINX Ingress controller flag for adding HTTP headers. Custom headers in NGINX Ingress are typically set via annotations like `nginx.ingress.kubernetes.io/configuration-snippet`. The question and answer are poorly sourced and likely incorrect/fictional.

### kcna-198
Answer D (awsElasticBlockStore). This volume type is deprecated in favor of CSI drivers. For modern Kubernetes the correct answer would be to use a StorageClass with a CSI provisioner via a PVC (option C). However, awsElasticBlockStore was historically the in-tree volume type. Defensible but technically deprecated.

### kcna-206
Answer B (count/services). Both `services` and `count/services` may work depending on Kubernetes version. In v1.15+, `count/services` is correct for object count quotas. In older versions, `services` was used. Defensible.

---

## Notes on Duplicate/Redundant Questions

The question set contains several groups of nearly identical questions that test the same concept repeatedly:
- kcna-024 and kcna-081 and kcna-114 and kcna-138 all ask about which field allocates a virtual IP
- kcna-033 and kcna-042 and kcna-086 and kcna-139 all ask about Recreate/RollingUpdate strategy
- kcna-070 and kcna-103 ask identical questions about spec.selector in a Service
- kcna-084 and kcna-168 ask identical questions about PodDisruptionBudget
- kcna-104, kcna-112, and kcna-147 ask about Linkerd injection (147 has wrong answer)
- kcna-093 and kcna-140 ask about Istio injection (both have answer sidecar.istio.io/inject but differ on value)
- kcna-135 and kcna-144 ask about Job selector (135 has wrong answer, 144 is correct)
- kcna-131 and kcna-141 and kcna-148 all ask about label+selector effects (131 has wrong answer)
- kcna-079 and kcna-134 and kcna-143 and kcna-150 ask about StatefulSet network identity (134 has wrong answer)
