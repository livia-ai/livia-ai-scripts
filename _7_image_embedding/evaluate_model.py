import torch
torch.cuda.empty_cache() 
from torch import nn
import torch.nn.functional as F
from torchvision import transforms

import livia.embedding as embedding
import livia.triplet as triplet
from dataset import TripletDataset, ImageDataset
from model import EmbeddingNet,TripletNet, train
from torch.utils.tensorboard import SummaryWriter

from tqdm import tqdm
import pandas as pd
import numpy as np
import pickle

#################################################################
# Create datasetembedding_loaded = embedding.load_csv("data/wm/wm_sbert_title_districts_subjects_256d.csv")
size = 50
batch_size = 64

# specify root directory that contains the images
root_dir = 'data/test_images/wm_cropped_train'

# specify transforms
transform = transforms.Compose([transforms.ToTensor(), transforms.CenterCrop(size)])

## load triplets
#triplets = []
#for i in range(6):
#    with open(f'data/triplets/15000/triplets_{i}', 'rb') as fp:
#        triplets_loaded = pickle.load(fp)
#        triplets.extend(triplets_loaded)
for trainset_size in [10000, 15000, 25000, 85000]:
    with open(f'data/wm/image_paths_for_dataset_nneighbors=15', 'rb') as fp:
        image_path_triplets = pickle.load(fp)[:trainset_size]

    ###############
    ## analyze triplets
    #from collections import defaultdict

    #sim_counts = defaultdict(int)
    #dis_counts = defaultdict(int)
    #sam_counts = defaultdict(int)
    #for sample, sim, dis in image_path_triplets:
    #    sam_counts[sample] += 1
    #    sim_counts[sim] += 1
    #    dis_counts[dis] += 1

    #print(len(image_path_triplets))
    #print(sorted(dis_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    #print(sorted(sim_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    #print(sorted(sam_counts.items(), key=lambda x: x[1], reverse=True)[:20])

    #############

    ## generate train and test dataset
    train_dataset = TripletDataset(samples = image_path_triplets,
                                root_dir = root_dir,
                                transform=transform)

    test_dataloader = torch.utils.data.DataLoader(train_dataset, batch_size=1, shuffle=False)
    ##################################################################


    ##################################################################
    # evaluate model

    # hyperparameters
    lr = 1e-4
    wd = 0
    n_epochs = 100
    margin = 1.5

    # load model
    log_dir = "experiments/runs/"
    run_name = f'centercropped={size}_triplets={trainset_size}_bs={batch_size}_margin={margin}_lr={lr}_wd={wd}_MaxP'
    triplet_model = torch.load(log_dir + run_name + "/triplet_net.pt")
    triplet_model = triplet_model.to(device="cuda")
    
    #for anchor, pos, neg in train_dataloader:
    #    print("in:", anchor.shape)
    #    anchor = anchor.to(device="cuda")
    #    pos = pos.to(device="cuda")
    #    neg = neg.to(device="cuda")
    #    anch_hidden, pos_hidden, neg_hidden = triplet_net(anchor, pos, neg)
    #    print("h:", anch_hidden.shape)
    #    break
    #error

    # create image embedding
    wm_data = pd.read_csv("data/wm/wien_museum.csv")
    wm_data = wm_data[["id", "title", "subjects"]]
    wm_data = wm_data.astype({"id": "str"})

    # load sentece embedding that should be used for computing triplets
    embedding_loaded = embedding.load_csv("data/wm/wm_sbert_title_districts_subjects_256d.csv")

    #img_dataset = ImageDataset(wm_data["id"], root_dir, transform)
    #img_dataloader = torch.utils.data.DataLoader(img_dataset, batch_size=1, shuffle=False)


    # only works if batch size is 1
    #print("Iterating over images...")
    with torch.no_grad():
        image_embedding_list = []
        id_list = []
        unique = set()
        for imgs in tqdm(test_dataloader):
            img, _,_, ori_path = imgs
            sample_id = ori_path[0].split(".")[0]

            if sample_id not in unique:
                img = img.to(device="cuda")
                encoded_img = triplet_model.encode(img)
                image_embedding_list.append(encoded_img.cpu().numpy()[0])

                unique.add(sample_id)
                id_list.append(sample_id)


    image_embedding = embedding.Embedding(np.array(image_embedding_list), np.array(id_list, dtype=object))
    embedding.save_to_csv(image_embedding, f"image_embedding_{trainset_size}")

    # plot sentence embedding
    n = 3000

    embedding.plot_3d(embedding_loaded, wm_data, n, 
                      "id", "title", "subjects", [], 
                      "Sentence Embedding")

    # take only samples from df where ids are in id_list
    meta_data = wm_data.loc[wm_data["id"].isin(id_list)]

    # plot image embedding
    embedding.plot_3d(image_embedding, meta_data, n, 
                    "id", "title", "subjects", [], 
                    f"Image Embedding stand: \n {run_name}", True)

    # plot image embedding
    embedding.plot_3d(image_embedding, meta_data, n, 
                    "id", "title", "subjects", [], 
                    f"Image Embedding: \n {run_name}", False)
