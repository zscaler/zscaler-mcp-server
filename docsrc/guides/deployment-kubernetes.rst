.. _deployment-kubernetes:

Kubernetes
==========

Deploy the Zscaler MCP Server to **any** Kubernetes cluster via Helm — EKS, GKE, AKS, OpenShift, Rancher, k3s, Talos, kind / minikube. The chart is cluster-vendor-agnostic and assumes you already have a cluster; if you'd rather stand up new cloud-managed infrastructure end-to-end, see the per-hyperscaler trees instead.

.. toctree::
   :maxdepth: 1

   helm-chart

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - When to use
   * - :doc:`Helm Chart <helm-chart>`
     - Install into an existing K8s cluster (any cloud, any distro, on-prem). Wires into ArgoCD / Flux / GitOps pipelines. Five credential paths from local dev to External Secrets Operator.
