"""
Problem Matcher — Tool that queries the curated coding problem dataset.
This is the "real tool call" that makes the agent more than just LLM prompting.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src import config

logger = logging.getLogger(__name__)

# Topic alias mapping — normalize LLM output to dataset tags
TOPIC_ALIASES = {
    "arrays_strings": ["arrays", "strings", "two_pointers", "sliding_window"],
    "arrays": ["arrays", "two_pointers", "sliding_window"],
    "strings": ["strings", "two_pointers"],
    "linked_lists": ["linked_lists"],
    "trees_graphs": ["trees", "graphs", "bfs", "dfs"],
    "trees": ["trees", "bfs", "dfs"],
    "graphs": ["graphs", "bfs", "dfs"],
    "dynamic_programming": ["dynamic_programming", "dp"],
    "dp": ["dynamic_programming", "dp"],
    "sorting_searching": ["sorting", "searching", "binary_search"],
    "binary_search": ["searching", "binary_search"],
    "stacks_queues": ["stacks", "queues"],
    "hash_maps": ["hash_maps", "hash_tables"],
    "recursion_backtracking": ["recursion", "backtracking"],
    "greedy": ["greedy"],
    "math_bit_manipulation": ["math", "bit_manipulation"],
    "sql": ["sql"],
    "system_design": ["system_design"],
    "oop_design_patterns": ["oop", "design_patterns"],
    "os_networking": ["os", "networking"],
    "behavioral": ["behavioral"],
    "api_design": ["system_design", "api_design"],
    "sql_databases": ["sql"],
}


class ProblemMatcher:
    """Queries the curated coding problem dataset."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or config.PROBLEMS_PATH
        self._problems: Optional[list[dict]] = None

    @property
    def problems(self) -> list[dict]:
        """Lazily load the problem dataset."""
        if self._problems is None:
            self._load_problems()
        return self._problems

    def _load_problems(self):
        """Load problems from JSON file."""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._problems = json.load(f)
            logger.info(f"[PROBLEM_MATCHER] Loaded {len(self._problems)} problems from {self.data_path}")
        except FileNotFoundError:
            logger.warning(f"[PROBLEM_MATCHER] Dataset not found at {self.data_path}, using empty list")
            self._problems = []
        except json.JSONDecodeError as e:
            logger.error(f"[PROBLEM_MATCHER] Invalid JSON in dataset: {e}")
            self._problems = []

    def _expand_topics(self, topics: list[str]) -> set[str]:
        """Expand topic names using aliases to match dataset tags."""
        expanded = set()
        for topic in topics:
            topic_lower = topic.lower().strip()
            if topic_lower in TOPIC_ALIASES:
                expanded.update(TOPIC_ALIASES[topic_lower])
            else:
                expanded.add(topic_lower)
        return expanded

    def match_problems(
        self,
        topics: list[str],
        difficulty_range: list[str] = None,
        count: int = 10,
    ) -> list[dict]:
        """
        Find problems matching the given topics and difficulty range.

        Args:
            topics: List of topic tags to match against.
            difficulty_range: List of acceptable difficulties, e.g. ["Easy", "Medium"].
            count: Max number of problems to return.

        Returns:
            List of problem dicts, sorted by relevance score (most relevant first).
        """
        if difficulty_range is None:
            difficulty_range = ["Easy", "Medium", "Hard"]

        expanded_topics = self._expand_topics(topics)
        difficulty_set = {d.capitalize() for d in difficulty_range}

        scored_problems = []
        for problem in self.problems:
            # Filter by difficulty
            if problem.get("difficulty", "").capitalize() not in difficulty_set:
                continue

            # Score by topic overlap
            problem_topics = set(t.lower() for t in problem.get("topics", []))
            overlap = expanded_topics & problem_topics
            if not overlap:
                continue

            score = len(overlap)
            # Bonus for matching more unique topics
            scored_problems.append((score, problem))

        # Sort by score descending, then by difficulty (Easy < Medium < Hard)
        difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}
        scored_problems.sort(
            key=lambda x: (-x[0], difficulty_order.get(x[1].get("difficulty", ""), 1))
        )

        # Take top N, ensuring topic diversity
        selected = []
        seen_titles = set()
        for _, problem in scored_problems:
            if problem["title"] not in seen_titles and len(selected) < count:
                selected.append(problem.copy())
                seen_titles.add(problem["title"])

        logger.info(
            f"[PROBLEM_MATCHER] Matched {len(selected)}/{len(self.problems)} problems "
            f"for topics: {', '.join(topics)} | difficulties: {', '.join(difficulty_range)}"
        )

        return selected

    def get_stats(self) -> dict:
        """Get dataset statistics."""
        topics_count: dict[str, int] = {}
        diff_count: dict[str, int] = {}
        for p in self.problems:
            for t in p.get("topics", []):
                topics_count[t] = topics_count.get(t, 0) + 1
            d = p.get("difficulty", "Unknown")
            diff_count[d] = diff_count.get(d, 0) + 1

        return {
            "total_problems": len(self.problems),
            "by_difficulty": diff_count,
            "by_topic": dict(sorted(topics_count.items(), key=lambda x: -x[1])),
        }
