"""
DataSentinel QA - Automated Data Profiler & Exploratory Data Analysis (EDA)
Computes deep statistical profiles for every column in the dataset:
Missing rates, distinct cardinalities, inferred data types, numerical distributions, and outliers.
"""

import math
import re
from typing import List, Dict, Any

class DataProfiler:
    @staticmethod
    def profile_dataset(rows: List[Dict]) -> Dict[str, Any]:
        """Profiles an entire list of row dictionaries and returns column-level telemetry."""
        if not rows:
            return {"total_rows": 0, "columns": []}

        total_rows = len(rows)
        columns = list(rows[0].keys())
        profiles = []

        for col in columns:
            vals = [r.get(col) for r in rows]
            non_empty = [v for v in vals if v is not None and str(v).strip() != ""]
            null_count = total_rows - len(non_empty)
            null_pct = round((null_count / total_rows) * 100, 2)
            distinct_count = len(set(non_empty))

            # Inferred Type Detection
            inferred_type = "string"
            num_vals = []
            
            # Test if numerical
            is_float = True
            is_int = True
            for v in non_empty[:200]: # Sample 200 for speed
                try:
                    f = float(v)
                    if "." in str(v):
                        is_int = False
                except ValueError:
                    is_float = False
                    is_int = False
                    break

            if is_int and non_empty:
                inferred_type = "integer"
            elif is_float and non_empty:
                inferred_type = "float"
            elif all("@" in str(v) for v in non_empty[:50]) and non_empty:
                inferred_type = "email"
            elif all(str(v).startswith("+") or str(v).isdigit() for v in non_empty[:50]) and non_empty:
                inferred_type = "phone"
            elif distinct_count <= 10:
                inferred_type = "categorical"

            # Numerical statistics if applicable
            stats = {}
            if inferred_type in ["integer", "float"]:
                for v in non_empty:
                    try:
                        num_vals.append(float(v))
                    except ValueError:
                        pass

                if num_vals:
                    num_vals.sort()
                    min_val = num_vals[0]
                    max_val = num_vals[-1]
                    mean_val = sum(num_vals) / len(num_vals)
                    median_val = num_vals[len(num_vals) // 2]
                    
                    variance = sum((x - mean_val) ** 2 for x in num_vals) / (len(num_vals) - 1 or 1)
                    std_dev = math.sqrt(variance)

                    # Outlier detection using Tukey's IQR rule (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
                    q1 = num_vals[int(len(num_vals) * 0.25)]
                    q3 = num_vals[int(len(num_vals) * 0.75)]
                    iqr = q3 - q1
                    lower_bound = q1 - (1.5 * iqr)
                    upper_bound = q3 + (1.5 * iqr)
                    outliers = [x for x in num_vals if x < lower_bound or x > upper_bound]

                    stats = {
                        "min": round(min_val, 2),
                        "max": round(max_val, 2),
                        "mean": round(mean_val, 2),
                        "median": round(median_val, 2),
                        "std_dev": round(std_dev, 2),
                        "outlier_count": len(outliers),
                        "outlier_pct": round((len(outliers) / len(num_vals)) * 100, 2)
                    }

            # Top 3 most frequent values
            freq_map = {}
            for v in non_empty:
                freq_map[v] = freq_map.get(v, 0) + 1
            sorted_freq = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)[:3]
            top_values = [{"value": k, "count": v, "pct": round((v / total_rows) * 100, 1)} for k, v in sorted_freq]

            profiles.append({
                "column": col,
                "inferred_type": inferred_type,
                "null_count": null_count,
                "null_pct": null_pct,
                "distinct_count": distinct_count,
                "stats": stats,
                "top_values": top_values
            })

        return {
            "total_rows": total_rows,
            "total_columns": len(columns),
            "columns": profiles
        }
