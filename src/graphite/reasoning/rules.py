"""Engineering rule checking, compliance auditing, and diagram anomaly detection."""

from typing import Dict, List, Optional, Set
import networkx as nx
from pydantic import BaseModel, Field

from graphite.core.models import BlueprintGraph


class AnomalyItem(BaseModel):
    """An identified blueprint anomaly or rule violation."""
    rule_id: str
    severity: str  # 'HIGH', 'MEDIUM', 'INFO'
    component_id: str
    component_label: str
    description: str


class ComplianceReport(BaseModel):
    """Complete blueprint engineering compliance audit."""
    blueprint_name: str
    total_components_checked: int
    anomalies: List[AnomalyItem] = Field(default_factory=list)
    passed_rules: List[str] = Field(default_factory=list)

    @property
    def has_critical_anomalies(self) -> bool:
        return any(a.severity == "HIGH" for a in self.anomalies)


class BlueprintRuleChecker:
    """Audits blueprint graphs against industrial engineering best practices."""

    def __init__(self, graph: BlueprintGraph):
        self.blueprint = graph
        self.nx_graph = graph.to_networkx(directed=False)

    def check_floating_equipment(self) -> List[AnomalyItem]:
        """Detect physical equipment completely disconnected from all lines (degree == 0)."""
        anomalies = []
        for nid, node in self.blueprint.get_physical_nodes().items():
            deg = self.nx_graph.degree(nid) if nid in self.nx_graph else 0
            if deg == 0:
                anomalies.append(
                    AnomalyItem(
                        rule_id="RULE-01-FLOATING-EQUIPMENT",
                        severity="HIGH",
                        component_id=nid,
                        component_label=node.label,
                        description=(
                            f"Physical component '{nid}' ({node.label}) has degree 0. "
                            f"It is floating without any pipe or signal connections."
                        ),
                    )
                )
        return anomalies

    def check_dead_end_valves(self) -> List[AnomalyItem]:
        """Detect valves connected to only a single line without downstream outlet or drain."""
        anomalies = []
        for nid, node in self.blueprint.get_physical_nodes().items():
            if "valve" in node.label.lower() and nid in self.nx_graph:
                deg = self.nx_graph.degree(nid)
                if deg == 1:
                    nbr = next(self.nx_graph.neighbors(nid))
                    nbr_lbl = self.nx_graph.nodes[nbr].get("label", "unknown")
                    anomalies.append(
                        AnomalyItem(
                            rule_id="RULE-02-DEAD-END-VALVE",
                            severity="MEDIUM",
                            component_id=nid,
                            component_label=node.label,
                            description=(
                                f"Valve '{nid}' is connected to only one component '{nbr}' ({nbr_lbl}). "
                                f"Missing downstream drain, cap, or flow continuation."
                            ),
                        )
                    )
        return anomalies

    def check_unisolated_vessels(self) -> List[AnomalyItem]:
        """Verify that tanks and vessels have an isolation valve within 2 hops on all lines."""
        anomalies = []
        for nid, node in self.blueprint.get_physical_nodes().items():
            if node.label in ("tank", "general") and nid in self.nx_graph:
                neighbors = list(self.nx_graph.neighbors(nid))
                for nbr in neighbors:
                    # Check if neighbor or neighbor's neighbor has a valve
                    nbr_lbl = self.nx_graph.nodes[nbr].get("label", "")
                    has_valve_in_2_hops = "valve" in nbr_lbl.lower()
                    if not has_valve_in_2_hops:
                        for nbr2 in self.nx_graph.neighbors(nbr):
                            nbr2_lbl = self.nx_graph.nodes[nbr2].get("label", "")
                            if nbr2 != nid and "valve" in nbr2_lbl.lower():
                                has_valve_in_2_hops = True
                                break

                    if not has_valve_in_2_hops and len(neighbors) > 0:
                        anomalies.append(
                            AnomalyItem(
                                rule_id="RULE-03-UNISOLATED-VESSEL-LINE",
                                severity="HIGH",
                                component_id=nid,
                                component_label=node.label,
                                description=(
                                    f"Vessel '{nid}' ({node.label}) connects to '{nbr}' ({nbr_lbl}) "
                                    f"without an inline isolation valve within 2 hops."
                                ),
                            )
                        )
        return anomalies

    def run_all_checks(self) -> ComplianceReport:
        """Run all engineering compliance rules and return an aggregated report."""
        anomalies: List[AnomalyItem] = []
        passed_rules: List[str] = []

        floating = self.check_floating_equipment()
        if floating:
            anomalies.extend(floating)
        else:
            passed_rules.append("RULE-01-FLOATING-EQUIPMENT")

        dead_ends = self.check_dead_end_valves()
        if dead_ends:
            anomalies.extend(dead_ends)
        else:
            passed_rules.append("RULE-02-DEAD-END-VALVE")

        unisolated = self.check_unisolated_vessels()
        if unisolated:
            anomalies.extend(unisolated)
        else:
            passed_rules.append("RULE-03-UNISOLATED-VESSEL-LINE")

        return ComplianceReport(
            blueprint_name=self.blueprint.name,
            total_components_checked=len(self.blueprint.get_physical_nodes()),
            anomalies=anomalies,
            passed_rules=passed_rules,
        )
