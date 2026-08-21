from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score


@dataclass
class FeatureImportanceResult:
    """
    Output of a trained feature-importance model.

    Attributes:
        feature_names: Column names used as model inputs, in the same
            order as `importances`.
        importances: Gradient-boosting feature importances (sums to ~1.0
            across all features), aligned to feature_names.
        train_r2 / test_r2: R^2 on the training and held-out test split.
            A large gap (high train_r2, near-zero or negative test_r2) is
            a sign the importances below describe an overfit model, not a
            real signal -- check this before trusting them.
        train_mae / test_mae: Mean absolute error on each split, in the
            same units as the label (e.g. 0.02 == 2% forward return).
        num_train_rows / num_test_rows: Size of each split, so a caller
            can sanity-check whether there was enough data at all.
    """

    feature_names: list[str]
    importances: list[float]
    train_r2: float
    test_r2: float
    train_mae: float
    test_mae: float
    num_train_rows: int
    num_test_rows: int

    def ranked_importances(self) -> list[tuple[str, float]]:
        """Feature/importance pairs, sorted most to least important."""
        pairs = list(zip(self.feature_names, self.importances))
        return sorted(pairs, key=lambda pair: pair[1], reverse=True)


class FeatureImportanceService:
    """
    Builds a labeled dataset (indicator readings -> forward N-day return)
    from an already-computed indicator DataFrame, trains a gradient
    boosting model with a CHRONOLOGICAL train/test split, and reports
    feature importances alongside train/test performance -- so the
    caller can judge whether those importances reflect a real,
    generalizing signal or an overfit model, rather than just reading
    .feature_importances_ off a model fit on everything.

    Depends on IndicatorService's OUTPUT (a DataFrame with indicator
    columns already computed) rather than recomputing indicators itself
    -- reuses whatever indicator set the caller already has instead of
    inventing a second indicator pipeline.
    """

    # Candidate feature columns, used only if present. Deliberately
    # excludes raw OHLCV (Open/High/Low/Close/Volume): using price levels
    # directly as "features" to predict a return derived from that same
    # price would leak the label into the inputs. Only derived indicators
    # are used as features.
    _CANDIDATE_FEATURES = [
        "RSI",
        "MACD",
        "MACD_Signal",
        "MACD_Histogram",
        "EMA20",
        "EMA50",
        "EMA200",
        "ATR",
        "Bollinger_Upper",
        "Bollinger_Lower",
        "Stoch_K",
        "Stoch_D",
    ]

    # Minimums below which a train/test split isn't meaningful enough to
    # trust -- an R^2/MAE computed on a handful of rows is closer to
    # noise than a real evaluation.
    _MIN_TOTAL_ROWS = 30
    _MIN_TRAIN_ROWS = 10
    _MIN_TEST_ROWS = 5

    def __init__(
        self,
        forward_days: int = 5,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> None:
        """
        Args:
            forward_days: N in "forward N-day return" -- the label for
                each row is the percentage return N trading days later.
            test_size: Fraction of rows held out for the test split,
                taken from the END of the series. This is a
                CHRONOLOGICAL split, never a random shuffle: shuffling
                time series data would let the model train on days
                adjacent to (and correlated with) its own test days,
                overstating how well it actually generalizes.
            random_state: Seed for the model's own internal randomness
                only -- has no effect on the train/test split, which is
                always chronological regardless of this value.
        """
        self._forward_days = forward_days
        self._test_size = test_size
        self._random_state = random_state

    def build_labeled_dataset(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """
        Build the (features..., forward_return) dataset from an indicator
        DataFrame.

        Args:
            indicators: DataFrame with a "Close" column and whichever
                indicator columns are available (as produced by
                IndicatorService.serve_indicators()).

        Returns:
            DataFrame indexed the same as `indicators`, containing only
            the available candidate feature columns plus
            "forward_return". Any row missing a feature or its label is
            dropped -- the trailing `forward_days` rows always lack a
            label (there's no future price yet to compute it from) and
            are dropped for exactly that reason.
        """
        available_features = [
            col for col in self._CANDIDATE_FEATURES if col in indicators.columns
        ]

        dataset = indicators[available_features].copy()
        dataset["forward_return"] = (
            indicators["Close"].shift(-self._forward_days) / indicators["Close"] - 1.0
        )

        return dataset.dropna()

    def train_and_evaluate(
        self,
        indicators: pd.DataFrame,
    ) -> FeatureImportanceResult | None:
        """
        Build the labeled dataset, split it chronologically, train a
        GradientBoostingRegressor, and report importances alongside
        train/test performance.

        Returns:
            FeatureImportanceResult, or None if there isn't enough usable
            data to both train and evaluate meaningfully (see the
            _MIN_*_ROWS thresholds), or no candidate feature columns are
            present in `indicators` at all. Never raises for these cases.
        """
        dataset = self.build_labeled_dataset(indicators)
        feature_names = [col for col in dataset.columns if col != "forward_return"]

        if not feature_names or len(dataset) < self._MIN_TOTAL_ROWS:
            return None

        split_index = int(len(dataset) * (1 - self._test_size))
        # Chronological split: earlier rows train, later rows test.
        train = dataset.iloc[:split_index]
        test = dataset.iloc[split_index:]

        if len(train) < self._MIN_TRAIN_ROWS or len(test) < self._MIN_TEST_ROWS:
            return None

        x_train, y_train = train[feature_names], train["forward_return"]
        x_test, y_test = test[feature_names], test["forward_return"]

        model = GradientBoostingRegressor(random_state=self._random_state)
        model.fit(x_train, y_train)

        train_predictions = model.predict(x_train)
        test_predictions = model.predict(x_test)

        return FeatureImportanceResult(
            feature_names=feature_names,
            importances=[float(value) for value in model.feature_importances_],
            train_r2=float(r2_score(y_train, train_predictions)),
            test_r2=float(r2_score(y_test, test_predictions)),
            train_mae=float(mean_absolute_error(y_train, train_predictions)),
            test_mae=float(mean_absolute_error(y_test, test_predictions)),
            num_train_rows=len(train),
            num_test_rows=len(test),
        )
