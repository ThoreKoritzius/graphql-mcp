"""
A professional visualization module that dynamically compares CSV experiments.

Each CSV must contain at least the columns:
  • question
  • num_tool_calls
  • total_tokens
  • total_cost
  • category
  • (optionally) tool_calls (a JSON-encoded array of tool call objects, each with a "tool" key)

If a CSV does not include a "success" column, success is assumed True when num_tool_calls > 0.

The script automatically creates a "plots" folder (if not present) and saves all figures there.
It produces several plots:
  • A horizontal bar-chart showing tool calls per question.
  • Grouped category-level bar-charts for average tool calls, success rate, total tokens, and total cost.
  • A stacked bar chart (one subplot per experiment) that, per category, displays the average breakdown of tool calls by tool name.
  • A frequency bar chart that shows overall counts of the tools used per experiment.
  
Usage:
  • By default, it uses a built-in configuration. To override,
    supply a JSON config file via the --config option:
    {
      "our": "results/result_apollo.csv",
      "test_1": "results/test_1.csv",
      "test_2": "results/test_2.csv"
    }
    
  Run with: python bench/viz.py --config path/to/config.json
"""

import os
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as mtick
import seaborn as sns

# Use a clean, professional style.
#plt.style.use("seaborn")
sns.set(style="whitegrid")

# Directory where plots are saved.
SAVE_DIR = "plots"

def ensure_save_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate dynamic, multi-aspect plots from CSV experiments."
    )
    parser.add_argument("--config", help="Path to JSON configuration file.")
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    return config

def load_data(file_path):
    df = pd.read_csv(file_path)
    # Ensure required columns are present.
    if "success" not in df.columns:
        df["success"] = df["num_tool_calls"] > 0
    return df

def bar_colors(success_series):
    # Green for success, red for failure.
    return ['#43A047' if str(s).lower() == 'true' or s is True else '#E53935'
            for s in success_series]

def plot_question_tool_calls(experiments):
    """
    Creates a horizontal grouped bar-chart for num_tool_calls per question.
    Assumes all experiments share the same set of questions.
    """
    # Use the first experiment’s questions as reference.
    base_key = list(experiments.keys())[0]
    base_df = experiments[base_key].sort_values("question").reset_index(drop=True)
    questions = base_df["question"]
    y = np.arange(len(questions))
    
    num_exps = len(experiments)
    total_height = 0.8   # total vertical space available for each question row
    bar_height = total_height / num_exps
    offset_adjust = (num_exps - 1) / 2
    
    fig, ax = plt.subplots(figsize=(13, 7))
    
    for i, (label, df) in enumerate(experiments.items()):
        df_sorted = df.sort_values("question").reset_index(drop=True)
        pos = y + (i - offset_adjust) * bar_height
        colors = bar_colors(df_sorted["success"])
        ax.barh(pos, df_sorted["num_tool_calls"], bar_height,
                color=colors, edgecolor="black", linewidth=1, label=label)
    
    ax.set_yticks(y)
    ax.set_yticklabels(questions)
    ax.invert_yaxis()   # highest question at the top
    ax.set_xlabel("Number of Tool Calls", fontsize=12)
    ax.set_title("Tool Calls per Question", fontsize=14, fontweight="bold")
    
    for i in range(len(questions)-1):
        ax.axhline(i + 0.5, color="gray", lw=1, alpha=0.7, linestyle="--")
    
    ax.set_xlim(left=-2)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "question_tool_calls.png"), dpi=300)
    plt.close(fig)

def plot_category_stats(experiments):
    """
    For each experiment, aggregate metrics by category and plot grouped bar-charts.
    Metrics include average tool calls, success rate, average total tokens, and average total cost.
    """
    agg_metrics = {
        "num_tool_calls": "mean",
        "total_tokens": "mean",
        "total_cost": "mean",
        "success": "mean"
    }
    agg_results = {}  # experiment label -> aggregated DataFrame
    for label, df in experiments.items():
        group = df.groupby("category").agg(agg_metrics).rename(columns={
            "num_tool_calls": "avg_tool_calls",
            "total_tokens": "avg_tokens",
            "total_cost": "avg_cost",
            "success": "success_rate"
        })
        agg_results[label] = group

    desired_order = ["easy", "hard", "adversarial"]
    categories = desired_order
    x = np.arange(len(categories))
    num_exps = len(agg_results)
    width = 0.7 / num_exps

    def plot_metric(metric, ylabel, title, file_name, yformatter=None, ylim=None, yticks=None):
        fig, ax = plt.subplots(figsize=(12, 6))
        for i, (label, group) in enumerate(agg_results.items()):
            values = group.reindex(categories)[metric].values
            ax.bar(x + (i - (num_exps-1)/2)*width, values, width, label=label)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=20, ha="right",
                           fontsize=14, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=13)
        ax.set_title(title, fontsize=15, fontweight="bold")
        if yformatter:
            ax.yaxis.set_major_formatter(yformatter)
        if ylim:
            ax.set_ylim(ylim)
        if yticks is not None:
            ax.set_yticks(yticks)
        ax.legend()
        ax.yaxis.grid(True, linestyle="--", linewidth=0.8, color="gray", alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(SAVE_DIR, file_name), dpi=300)
        plt.close(fig)
    
    plot_metric("avg_tool_calls",
                "Average Tool Calls",
                "Average Tool Calls per Category",
                "category_tool_calls.png")
    
    plot_metric("success_rate",
                "Success Rate",
                "Success Rate per Category",
                "category_success_rate.png",
                yformatter=mtick.PercentFormatter(xmax=1.0),
                ylim=(0, 1.05),
                yticks=np.arange(0, 1.01, 0.2))
    
    plot_metric("avg_tokens",
                "Average Total Tokens",
                "Average Total Tokens per Category",
                "category_total_tokens.png")
    
    plot_metric("avg_cost",
                "Average Total Cost",
                "Average Total Cost per Category",
                "category_total_cost.png")

def parse_tool_calls(df):
    """
    Parse the "tool_calls" column for each row in the DataFrame.
    Returns a new DataFrame with columns: category and a dictionary mapping tool names to counts.
    Assumes each row's tool_calls is a JSON-encoded array of dictionaries containing a "tool" key.
    If the column does not exist, returns None.
    """
    if "tool_calls" not in df.columns:
        return None
    
    records = []
    for _, row in df.iterrows():
        cat = row["category"]
        tool_counter = {}
        try:
            calls = json.loads(row["tool_calls"])
        except Exception:
            calls = []
        for call in calls:
            tool = call.get("tool", "Unknown")
            tool_counter[tool] = tool_counter.get(tool, 0) + 1
        records.append({"category": cat, "tool_counter": tool_counter})
    return pd.DataFrame(records)

def plot_stacked_tool_calls_by_category(experiments):
    """
    For each experiment that has a "tool_calls" column,
    create a subplot with a stacked bar chart (categories on the x-axis)
    and segments representing average counts of each tool (averaged per row within that category).
    """
    desired_categories = ["easy", "hard", "adversarial"]
    num_exps = len(experiments)
    # Determine subplot layout: one row per experiment.
    fig, axes = plt.subplots(num_exps, 1, figsize=(12, 6*num_exps), squeeze=False)
    
    for idx, (label, df) in enumerate(experiments.items()):
        parsed = parse_tool_calls(df)
        if parsed is None:
            print(f"Experiment {label} has no 'tool_calls' column. Skipping stacked plot.")
            continue
        
        # Group by category. For each category, average counts per row.
        d = {cat: {} for cat in desired_categories}
        for _, row in parsed.iterrows():
            cat = row["category"]
            if cat not in desired_categories:
                continue
            # Add counts from this row.
            for tool, cnt in row["tool_counter"].items():
                d[cat][tool] = d[cat].get(tool, 0) + cnt
        # Count how many rows per category:
        count_per_cat = parsed.groupby("category").size().reindex(desired_categories).fillna(0)
        
        # Create DataFrame for plotting: rows=categories, columns=tools, values=average count.
        plot_data = {}
        all_tools = set()
        for cat in desired_categories:
            all_tools.update(d[cat].keys())
        for tool in all_tools:
            avg_counts = []
            for cat in desired_categories:
                total = d[cat].get(tool, 0)
                n = count_per_cat.get(cat, 0)
                avg = total / n if n > 0 else 0
                avg_counts.append(avg)
            plot_data[tool] = avg_counts
        plot_df = pd.DataFrame(plot_data, index=desired_categories)
        
        ax = axes[idx][0]
        bottom = np.zeros(len(desired_categories))
        colors = sns.color_palette("husl", n_colors=len(plot_df.columns))
        for i, tool in enumerate(plot_df.columns):
            ax.bar(desired_categories, plot_df[tool], bottom=bottom,
                   label=tool, color=colors[i])
            bottom += plot_df[tool].values
        ax.set_xlabel("Category", fontsize=12)
        ax.set_ylabel("Average Tool Call Count", fontsize=12)
        ax.set_title(f"Stacked Tool Calls by Category ({label})", fontsize=14, fontweight="bold")
        ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "stacked_tool_calls_by_category.png"), dpi=300)
    plt.close(fig)

def plot_overall_tool_call_frequency(experiments):
    """
    For each experiment with a "tool_calls" column, aggregate overall tool counts (ignoring category)
    and then plot a grouped bar chart where each experiment has bars for each tool.
    """
    overall_freq = {}
    all_tools = set()
    for label, df in experiments.items():
        parsed = parse_tool_calls(df)
        if parsed is None:
            continue
        counter = {}
        for _, row in parsed.iterrows():
            for tool, cnt in row["tool_counter"].items():
                counter[tool] = counter.get(tool, 0) + cnt
                all_tools.add(tool)
        overall_freq[label] = counter
    
    if not overall_freq:
        print("No experiment has the 'tool_calls' column. Skipping overall tool frequency plot.")
        return
    
    all_tools = sorted(list(all_tools))
    # Build a DataFrame: rows=experiment, columns=tools, values=count.
    data = []
    labels = []
    for label, counter in overall_freq.items():
        row = [counter.get(tool, 0) for tool in all_tools]
        data.append(row)
        labels.append(label)
    df_freq = pd.DataFrame(data, columns=all_tools, index=labels)
    
    # Plot as grouped bar chart.
    x = np.arange(len(all_tools))
    num_exps = len(df_freq)
    width = 0.8 / num_exps
    
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, label in enumerate(df_freq.index):
        values = df_freq.loc[label].values
        ax.bar(x + (i - (num_exps-1)/2)*width, values, width, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(all_tools, rotation=45, ha="right", fontsize=12)
    ax.set_ylabel("Overall Tool Call Frequency", fontsize=12)
    ax.set_title("Overall Frequency of Tool Calls per Experiment", fontsize=14, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "overall_tool_call_frequency.png"), dpi=300)
    plt.close(fig)

def main(config, dataset_name="", drop_unrelated=True):
    ensure_save_dir(SAVE_DIR)
    experiments = {}
    for key, value in config.items():
        if key == "top_k":
            continue
        df = load_data(value)
        if drop_unrelated:
            df = df[df["category"] != "unrelated"].reset_index(drop=True)
        experiments[key] = df
    
    # Optionally, if you want to limit to the first top_k rows:
    if "top_k" in config:
        top_k = config["top_k"]
        for key in experiments:
            experiments[key] = experiments[key].head(top_k)
    
    # Generate plots.
    plot_question_tool_calls(experiments)
    plot_category_stats(experiments)
    plot_stacked_tool_calls_by_category(experiments)
    plot_overall_tool_call_frequency(experiments)
    plot_category_stats_box(experiments, dataset_name)
    print("All plots have been generated and saved in the 'plots' folder.")

def plot_category_stats_box(experiments, dataset_name):
    """
    Create slide-friendly box plots of metrics by category for multiple experiments.
    Metrics: num_tool_calls, success, total_tokens, latency_seconds.
    Exports 16:9 figures with larger fonts and readable styling.
    """
    metrics = [
        ("num_tool_calls", "Number of Tool Calls", "Tool Calls per Category", "box_category_tool_calls.png"),
        ("success", "Success (1=True, 0=False)", "Success Rate per Category", "box_category_success.png"),
        ("total_tokens", "Total Tokens", "Tokens per Category", "box_category_tokens.png"),
        ("latency_seconds", "Latency (seconds)", "Latency per Category", "box_category_latency.png"),
    ]

    for metric, ylabel, title, file_name in metrics:
        # Combine all experiments into one DataFrame with experiment label
        combined = []
        for label, df in experiments.items():
            if metric not in df.columns:
                continue
            temp = df.copy()
            if metric == "success":
                temp[metric] = temp[metric].astype(int)
            temp["experiment"] = label
            combined.append(temp)
        if not combined:
            continue

        df_all = pd.concat(combined, ignore_index=True)

        # 16:9 figure, slide-friendly size
        fig, ax = plt.subplots(figsize=(16, 9))
        
        # Box plot
        sns.boxplot(
            data=df_all,
            x="category",
            y=metric,
            hue="experiment",
            ax=ax,
            palette="Set2",
            linewidth=2,
            fliersize=6
        )
        # Strip plot for individual points
        sns.stripplot(
            data=df_all,
            x="category",
            y=metric,
            hue="experiment",
            dodge=True,
            ax=ax,
            alpha=0.6,
            linewidth=1,
            size=8,
            palette="Set2"
        )

        # Limit y-axis to 95th percentile for readability
        upper = df_all[metric].quantile(0.95)
        ax.set_ylim(0, upper * 1.1)

        # Slide-friendly styling
        ax.set_xlabel("", fontsize=18)
        ax.set_ylabel(ylabel, fontsize=20)
        ax.set_title(f"{title}, {dataset_name}", fontsize=24, fontweight="bold")
        ax.tick_params(axis='x', labelsize=18)
        ax.tick_params(axis='y', labelsize=18)
        ax.grid(True, linestyle="--", linewidth=1, alpha=0.7)

        # Secondary y-axis for total_tokens -> cost
        if metric == "total_tokens":
            ax2 = ax.twinx()
            scaling_factors = []
            for label, df in experiments.items():
                if "total_cost" in df.columns and "total_tokens" in df.columns:
                    factor = df["total_cost"].sum() / df["total_tokens"].sum()
                    scaling_factors.append(factor)
            if scaling_factors:
                avg_factor = np.mean(scaling_factors)
                ax2.set_ylim(ax.get_ylim()[0]*avg_factor, ax.get_ylim()[1]*avg_factor)
                ax2.set_ylabel("Cost", fontsize=20)
                ax2.tick_params(axis='y', labelsize=18)
                ax2.grid(False)

        # Clean legend: remove duplicates from stripplot
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[:len(experiments)], labels[:len(experiments)], title=None,
                  fontsize=16, title_fontsize=18, loc='upper right')

        plt.tight_layout(pad=3)
        plt.savefig(os.path.join(SAVE_DIR, file_name), dpi=300)
        plt.close(fig)



if __name__ == "__main__":
    args = parse_args()
    if args.config:
        config = load_config(args.config)
    else:
        # Default configuration; update CSV paths as needed.
        config = {
            "A1: Predefined Tools": "results/result_apollo.csv",
            "A2: Schema Discovery": "results/result_apollo.csv",
            "A3: Full Introspection": "results/result_20250901_211437.csv",
        }
    main(config, dataset_name="The Space Devs, GPT-4.1")