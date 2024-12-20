from typing import Dict

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.datasets import RetrieverDataset

from .utils import tokenize_and_stem


class CTRBM25Okapi(BM25Okapi):
    """
    Slightly modified version of the BM25Okapi that takes into consideration the statement id, type, and section

    """

    def __init__(
        self,
        corpus: RetrieverDataset,
        tokenizer=None,
        k1=1.5,
        b=0.75,
        epsilon=0.25,
        top_k=5,
    ) -> None:
        print("Initialising BM25")
        self.corpus_df = pd.DataFrame(corpus.data)

        self.top_k = top_k

        corpus = []
        for evidence, statement in self.corpus_df[["evidence", "statement"]].values:
            processed_evidence = tokenize_and_stem(evidence)
            processed_statement = tokenize_and_stem(statement)
            corpus += [processed_evidence + processed_statement]

        super().__init__(corpus, tokenizer, k1, b, epsilon)

    def get_document_scores(
        self, query, section, type, statement_id
    ) -> Dict[str, list]:
        # Given the section and type, narrow down the search space
        relevant_docs = self.corpus_df.loc[
            (self.corpus_df["section"] == section) & (self.corpus_df["type"] == type)
        ]

        doc_ids = relevant_docs.index.tolist()

        # Tokenize and stem query
        processed_query = tokenize_and_stem(query)

        # Get BM25 score
        scores = self.get_batch_scores(processed_query, doc_ids)

        # Rank documents based on scores
        ranked_documents = sorted(
            zip(doc_ids, scores), key=lambda x: x[1], reverse=True
        )

        # Print the most similar documents
        # k examples for contradiction and entailment
        relevant_contradiction_examples = []
        relevant_entailment_examples = []
        for idx, score in ranked_documents:
            doc = self.corpus_df.iloc[idx]
            if statement_id == doc["id"]:
                # Filter out the sentence itself if found in the ranking
                continue
            else:
                if doc["labels"].lower() == "contradiction":
                    # Take only top k examples per label
                    if len(relevant_contradiction_examples) >= self.top_k:
                        continue
                    relevant_contradiction_examples += [
                        {
                            "id": doc["id"],
                            "score": score,
                        }
                    ]
                elif doc["labels"].lower() == "entailment":
                    # Take only top k examples per label
                    if len(relevant_entailment_examples) >= self.top_k:
                        continue
                    relevant_entailment_examples += [
                        {
                            "id": doc["id"],
                            "score": score,
                        }
                    ]

            # Take only top k examples
            if (
                len(relevant_contradiction_examples) >= self.top_k
                and len(relevant_entailment_examples) >= self.top_k
            ):
                break

        return {
            "contradictions": relevant_contradiction_examples,
            "entailments": relevant_entailment_examples,
        }
