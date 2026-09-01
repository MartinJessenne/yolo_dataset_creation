"""Entraine une variante de segmentation RF-DETR sur le dataset de chariots.

Les trois variantes ne different pas seulement par leur profondeur : leur
resolution d'entree est figee dans leurs poids pre-entraines
(positional_encoding_size = resolution / patch_size), 312 pour nano, 384 pour
small, 432 pour medium. Cette resolution ne se regle donc pas, elle fait partie
de la variante -- et c'est elle qui porte l'essentiel de l'arbitrage
precision/latence que ce script sert a mesurer.

Tout le reste est tenu identique d'une variante a l'autre (memes epochs, meme
taille de lot effective, meme dataset, meme graine), sans quoi la comparaison
ne mesurerait plus la variante mais le protocole.
"""
import argparse
import json
import os
import time

import torch
from rfdetr import RFDETRSegMedium, RFDETRSegNano, RFDETRSegSmall

VARIANTES = {
    "nano": (RFDETRSegNano, 312),
    "small": (RFDETRSegSmall, 384),
    "medium": (RFDETRSegMedium, 432),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variante", choices=sorted(VARIANTES))
    ap.add_argument("--dataset-dir", default="_rfdetr_dataset")
    ap.add_argument("--epochs", type=int, default=10)
    # Taille de lot effective = batch_size * grad_accum_steps. RF-DETR est reglee
    # pour 16 en affinage ; la carte a 96 GB, donc les 16 tiennent en un seul lot
    # et grad_accum reste a 1 pour les trois variantes.
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--grad-accum-steps", type=int, default=1)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    cls, resolution = VARIANTES[args.variante]
    output_dir = args.output_dir or f"output/seg_{args.variante}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"variante   : {args.variante}  (resolution {resolution})")
    print(f"gpu        : {torch.cuda.get_device_name(0)}")
    print(f"capability : {torch.cuda.get_device_capability()}")
    print(f"dataset    : {args.dataset_dir}")
    print(f"sortie     : {output_dir}\n")

    debut = time.time()
    modele = cls()
    modele.train(
        dataset_dir=args.dataset_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum_steps,
        output_dir=output_dir,
    )
    duree = time.time() - debut

    resume = {
        "variante": args.variante,
        "resolution": resolution,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "grad_accum_steps": args.grad_accum_steps,
        "duree_entrainement_s": round(duree, 1),
        "gpu": torch.cuda.get_device_name(0),
    }
    with open(os.path.join(output_dir, "resume_entrainement.json"), "w") as fh:
        json.dump(resume, fh, indent=2)
    print(f"\ntermine en {duree/60:.1f} min -> {output_dir}")


if __name__ == "__main__":
    main()
