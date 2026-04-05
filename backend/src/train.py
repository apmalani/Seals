import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
    roc_auc_score, roc_curve, confusion_matrix, ConfusionMatrixDisplay)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, label_binarize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import conf


def do_train(df):
    os.makedirs(conf.MODELS_DIR, exist_ok=True)
    os.makedirs(conf.RESULTS_DIR, exist_ok=True)

    X = df[conf.ALL_FEATS].values
    y = df["target"].values

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=conf.TEST_SZ, stratify=y, random_state=conf.SEED)

    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(Xtr)
    Xte_s = scaler.transform(Xte)

    mdl = LogisticRegression(max_iter=1000, random_state=conf.SEED)
    mdl.fit(Xtr_s, ytr)

    yp = mdl.predict(Xte_s)
    yprob = mdl.predict_proba(Xte_s)[:,1]
    acc = accuracy_score(yte, yp)
    roc = roc_auc_score(yte, yprob)

    print(classification_report(yte, yp, target_names=["no seal", "seal"]))
    print("acc=%.4f roc-auc=%.4f" % (acc, roc))

    coef = mdl.coef_[0]
    b0 = mdl.intercept_[0]
    mu = scaler.mean_
    sig = scaler.scale_

    raw_b = coef / sig
    raw_b0 = b0 - np.sum(coef * mu / sig)

    lines = ["P(seal) = 1 / (1 + exp(-z))", ""]
    lines.append("z = %+.6f" % raw_b0)
    for nm, b in zip(conf.ALL_FEATS, raw_b):
        lines.append("  %+.10f * %s" % (b, nm))

    txt = "\n".join(lines)
    print(txt)
    with open(conf.EQ_TXT, "w") as fh:
        fh.write(txt + "\n")

    joblib.dump(mdl, conf.MODEL_PKL)
    joblib.dump(scaler, conf.SCALER_PKL)
    print("model -> " + conf.MODEL_PKL)

    return {"acc": acc, "roc": roc, "equation": txt,
            "n_train": len(ytr), "n_test": len(yte),
            "coef": raw_b, "intercept": raw_b0,
            "yte": yte, "yprob": yprob}


def train_species(df):
    os.makedirs(conf.MODELS_DIR, exist_ok=True)

    pos = df[(df["target"] == 1) & (df["species"] != "") & (df["species"] != "unknown_phocidae")].copy()
    if pos.empty:
        print("no species data, skipping stage 2")
        return None

    counts = pos["species"].value_counts()
    print("\nspecies counts before lumping:")
    for sp, ct in counts.items():
        print("  %s: %d" % (sp, ct))

    rare = counts[counts < conf.MIN_SPECIES_COUNT].index
    if len(rare) > 0:
        pos.loc[pos["species"].isin(rare), "species"] = "other_phocidae"
        print("lumped %d rare species -> other_phocidae" % len(rare))

    counts2 = pos["species"].value_counts()
    print("\nspecies counts for training:")
    for sp, ct in counts2.items():
        print("  %s: %d" % (sp, ct))
    print("total: %d rows, %d classes" % (len(pos), len(counts2)))

    X = pos[conf.ALL_FEATS].values
    y = pos["species"].values

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=conf.TEST_SZ, stratify=y, random_state=conf.SEED)

    sc = StandardScaler()
    Xtr_s = sc.fit_transform(Xtr)
    Xte_s = sc.transform(Xte)

    mdl = LogisticRegression(solver="lbfgs",
        max_iter=2000, class_weight="balanced", random_state=conf.SEED)
    mdl.fit(Xtr_s, ytr)

    yp = mdl.predict(Xte_s)
    yprob = mdl.predict_proba(Xte_s)
    acc = accuracy_score(yte, yp)
    report = classification_report(yte, yp)
    print("\n--- stage 2: species model ---")
    print(report)
    print("species acc=%.4f" % acc)

    roc = None
    try:
        roc = roc_auc_score(yte, yprob, multi_class="ovr", average="macro")
        print("species macro roc-auc=%.4f" % roc)
    except Exception:
        pass

    classes = list(mdl.classes_)
    joblib.dump(mdl, conf.SPECIES_MODEL_PKL)
    joblib.dump(sc, conf.SPECIES_SCALER_PKL)
    joblib.dump(classes, conf.SPECIES_CLASSES_PKL)
    print("species model -> " + conf.SPECIES_MODEL_PKL)

    print("\nsample top-%d predictions:" % conf.TOP_K)
    rng = np.random.default_rng(conf.SEED)
    sample_idx = rng.choice(len(Xte), size=min(3, len(Xte)), replace=False)
    samples = []
    for i in sample_idx:
        probs = mdl.predict_proba(Xte_s[i:i+1])[0]
        order = np.argsort(probs)[::-1][:conf.TOP_K]
        print("  actual=%s" % yte[i])
        preds = []
        for rank, idx in enumerate(order):
            print("    %d. %s (%.1f%%)" % (rank+1, classes[idx], probs[idx]*100))
            preds.append((classes[idx], probs[idx]*100))
        print()
        samples.append((yte[i], preds))

    return {"acc": acc, "roc": roc, "report": report,
            "counts_raw": counts, "counts_train": counts2,
            "n_train": len(ytr), "n_test": len(yte),
            "classes": classes, "samples": samples,
            "yte": yte, "yp": yp, "yprob": yprob}


def make_plots(s1, s2):
    os.makedirs(conf.RESULTS_DIR, exist_ok=True)

    fpr, tpr, _ = roc_curve(s1["yte"], s1["yprob"])
    sea_blue = "#1a7fad"
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.fill_between(fpr, 0, tpr, color=sea_blue, alpha=0.32, zorder=1, linewidth=0)
    ax.plot(
        fpr,
        tpr,
        linewidth=2.2,
        color=sea_blue,
        label="AUC = %.3f" % s1["roc"],
        zorder=2,
    )
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, zorder=3)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC - Seal Presence (Stage 1)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(conf.ROC_S1_PNG, dpi=150)
    plt.close(fig)
    print("plot -> " + conf.ROC_S1_PNG)

    if s2 is not None:
        classes = s2["classes"]
        yte = s2["yte"]
        yprob = s2["yprob"]
        yte_bin = label_binarize(yte, classes=classes)

        fig, ax = plt.subplots(figsize=(8, 6))
        for i, sp in enumerate(classes):
            fpr_i, tpr_i, _ = roc_curve(yte_bin[:, i], yprob[:, i])
            auc_i = roc_auc_score(yte_bin[:, i], yprob[:, i])
            ax.plot(fpr_i, tpr_i, linewidth=1.5, label="%s (%.3f)" % (sp, auc_i))
        ax.plot([0, 1], [0, 1], "k--", linewidth=0.8)
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("ROC - Species ID, One-vs-Rest (Stage 2)")
        ax.legend(loc="lower right", fontsize=7)
        fig.tight_layout()
        fig.savefig(conf.ROC_S2_PNG, dpi=150)
        plt.close(fig)
        print("plot -> " + conf.ROC_S2_PNG)

        cm = confusion_matrix(yte, s2["yp"], labels=classes, normalize="true")
        fig, ax = plt.subplots(figsize=(9, 8))
        disp = ConfusionMatrixDisplay(cm, display_labels=classes)
        disp.plot(
            ax=ax,
            cmap="Blues",
            values_format=".2f",
            xticks_rotation=45,
            colorbar=False,
        )
        ax.set_title("Confusion Matrix - Species (normalized)")
        fig.tight_layout()
        fig.savefig(conf.CONFUSION_PNG, dpi=150)
        plt.close(fig)
        print("plot -> " + conf.CONFUSION_PNG)

    top_n = 7
    ranked = sorted(
        zip(conf.ALL_FEATS, np.abs(s1["coef"])), key=lambda x: x[1], reverse=True
    )[:top_n]
    feat_imp = sorted(ranked, key=lambda x: x[1])
    names = [x[0] for x in feat_imp]
    vals = [x[1] for x in feat_imp]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(range(len(names)), vals)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("|Coefficient| (raw scale)")
    ax.set_title("Feature importance — top %d (Stage 1 seal presence)" % top_n)
    fig.tight_layout()
    fig.savefig(conf.FEAT_IMP_PNG, dpi=150)
    plt.close(fig)
    print("plot -> " + conf.FEAT_IMP_PNG)


def dump_results(df, s1, s2):
    os.makedirs(conf.RESULTS_DIR, exist_ok=True)
    out = []
    out.append("=" * 60)
    out.append("SEAL SDM RESULTS")
    out.append("=" * 60)

    n_pos = int((df["target"] == 1).sum())
    n_neg = int((df["target"] == 0).sum())
    out.append("")
    out.append("dataset: %d total rows (%d presence, %d pseudo-absence)" % (len(df), n_pos, n_neg))
    out.append("features: %d" % len(conf.ALL_FEATS))
    out.append("test split: %.0f%%" % (conf.TEST_SZ * 100))
    out.append("")

    out.append("-" * 60)
    out.append("STAGE 1: SEAL PRESENCE (binary logistic regression)")
    out.append("-" * 60)
    out.append("train: %d  test: %d" % (s1["n_train"], s1["n_test"]))
    out.append("accuracy:  %.4f" % s1["acc"])
    out.append("roc-auc:   %.4f" % s1["roc"])
    out.append("")
    out.append(s1["equation"])
    out.append("")

    feat_imp = sorted(zip(conf.ALL_FEATS, np.abs(s1["coef"])), key=lambda x: -x[1])
    out.append("feature importance (|raw coef|):")
    for nm, v in feat_imp:
        out.append("  %-35s %.8f" % (nm, v))

    if s2 is None:
        out.append("")
        out.append("stage 2 skipped (no species data)")
    else:
        out.append("")
        out.append("-" * 60)
        out.append("STAGE 2: SPECIES ID (multinomial logistic regression)")
        out.append("-" * 60)
        out.append("train: %d  test: %d  classes: %d" % (s2["n_train"], s2["n_test"], len(s2["classes"])))
        out.append("accuracy:       %.4f" % s2["acc"])
        if s2["roc"] is not None:
            out.append("macro roc-auc:  %.4f" % s2["roc"])
        out.append("")

        out.append("species distribution:")
        out.append("  %-35s %8s" % ("species", "records"))
        out.append("  " + "-" * 45)
        for sp, ct in s2["counts_raw"].items():
            out.append("  %-35s %8d" % (sp, ct))
        out.append("  " + "-" * 45)
        out.append("  %-35s %8d" % ("TOTAL", s2["counts_raw"].sum()))

        if len(s2["counts_raw"]) != len(s2["counts_train"]):
            out.append("")
            out.append("after lumping (min %d per species):" % conf.MIN_SPECIES_COUNT)
            for sp, ct in s2["counts_train"].items():
                out.append("  %-35s %8d" % (sp, ct))

        out.append("")
        out.append("per-species classification report:")
        for line in s2["report"].strip().split("\n"):
            out.append("  " + line)

        out.append("")
        out.append("sample predictions (top %d):" % conf.TOP_K)
        for actual, preds in s2["samples"]:
            out.append("  actual: %s" % actual)
            for rank, (sp, pct) in enumerate(preds):
                out.append("    %d. %-30s %5.1f%%" % (rank + 1, sp, pct))
            out.append("")

    out.append("")
    out.append("=" * 60)
    out.append("notes:")
    out.append("- stage 1 predicts P(seal present | environment)")
    out.append("- stage 2 predicts P(species | seal present, environment)")
    out.append("- combined: P(species X) = P(seal) * P(species X | seal)")
    out.append("- pseudo-absences: coastal-biased within %d km of shore" % int(conf.MAX_SHORE_KM))
    out.append("- sst imputed to -1.8 C (seawater freezing) where missing")
    out.append("- wind from NCEP reanalysis monthly means")
    out.append("- class_weight=balanced used for species model")
    out.append("=" * 60)

    txt = "\n".join(out)
    with open(conf.RESULTS_TXT, "w") as fh:
        fh.write(txt + "\n")
    print("results -> " + conf.RESULTS_TXT)
