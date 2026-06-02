from app.agents.state import AxonState, DevMetrics, Anomaly
from datetime import datetime

BURNOUT_AFTER_HOUR = 20
HIGH_CHURN_THRESHOLD = 500

async def run(state: AxonState) -> dict:
    commits = state.get("commits", [])
    prs = state.get("prs", [])
    developers = state.get("developers", [])
    
    dev_commits = {d["id"]: [] for d in developers}
    for c in commits:
        if c.get("developer_id") in dev_commits:
            dev_commits[c["developer_id"]].append(c)
            
    dev_prs = {d["id"]: [] for d in developers}
    for p in prs:
        if p.get("developer_id") in dev_prs:
            dev_prs[p["developer_id"]].append(p)
            
    metrics = {}
    anomalies = []
    
    for dev in developers:
        dev_id = dev["id"]
        d_commits = dev_commits[dev_id]
        d_prs = dev_prs[dev_id]
        
        commit_count = len(d_commits)
        
        after_hours_count = 0
        high_churn_count = 0
        
        for c in d_commits:
            if c.get("committed_at"):
                dt = datetime.fromisoformat(c["committed_at"])
                if dt.hour >= BURNOUT_AFTER_HOUR or dt.hour < 6:
                    after_hours_count += 1
                    
        for p in d_prs:
            added = p.get("additions", 0) or 0
            removed = p.get("deletions", 0) or 0
            if added > 0 and removed > 2 * added:
                high_churn_count += 1
            elif added == 0 and removed > 50:
                high_churn_count += 1
                
        after_hours_ratio = after_hours_count / commit_count if commit_count > 0 else 0.0
        
        merged_prs = [p for p in d_prs if p.get("time_to_merge_h") is not None]
        avg_merge_h = sum(p["time_to_merge_h"] for p in merged_prs) / len(merged_prs) if merged_prs else None
        
        score = 100.0
        if commit_count == 0:
            score -= 30
        if after_hours_ratio > 0.4:
            score -= 25
            anomalies.append(Anomaly(
                type="burnout_risk",
                developer_id=dev_id,
                detail=f"{after_hours_ratio*100:.1f}% commits after hours",
                severity="critical"
            ))
        if high_churn_count > 0:
            score -= 15
            anomalies.append(Anomaly(
                type="high_churn",
                developer_id=dev_id,
                detail=f"{high_churn_count} PRs with high churn (deletions > 2*additions)",
                severity="warning"
            ))
        if avg_merge_h is not None and avg_merge_h > 72:
            score -= 20
            anomalies.append(Anomaly(
                type="slow_review",
                developer_id=dev_id,
                detail=f"Average PR merge time is {avg_merge_h:.1f}h",
                severity="warning"
            ))
            
        score = max(0.0, score)
        
        metrics[dev_id] = DevMetrics(
            developer_id=dev_id,
            commit_count=commit_count,
            after_hours_ratio=after_hours_ratio,
            high_churn_count=high_churn_count,
            avg_merge_h=avg_merge_h,
            health_score=score
        )
        
    team_metrics = {
        "total_commits": len(commits),
        "total_prs": len(prs),
        "avg_health_score": sum(m["health_score"] for m in metrics.values()) / len(metrics) if metrics else 100.0,
        "developer_count": len(developers)
    }
    
    return {
        "developer_metrics": metrics,
        "team_metrics": team_metrics,
        "anomalies": anomalies
    }
