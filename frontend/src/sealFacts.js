const sealFacts = [
  {
    scientific_name: "Mirounga leonina",
    common_name: "Southern elephant seal",
    images: [
      "https://www.asoc.org/wp-content/uploads/2023/10/Male-elephant-seal-e1712190928510-775x650.jpg", "https://ocean.si.edu/sites/default/files/styles/full_width_large/public/2023-11/NBPOV2012_JustinHofman_ElephantSeal.jpg.webp?itok=hlkFoasU"
    ],
    fun_facts: [
      "Deepest-diving non-cetacean, reaching depths over 2,100 meters.",
      "Largest pinniped, with males weighing up to 4,000 kg.",
      "Can hold its breath for more than two hours during dives.",
      "Extreme sexual dimorphism; males are up to five times heavier than females.",
      "Spend about 90% of their time at sea underwater."
    ]
  },
  {
    scientific_name: "Leptonychotes weddellii",
    common_name: "Weddell seal",
    images: [
      "https://www.antarctica.gov.au/site/assets/files/45640/weddell-seal.800x450.jpg?nc=b048", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrLamtJLeCrnnMv-gi-SL0-TlDp4QAafsXIkBAukDEy0ctHt33Sl0KF1eVYGBfCet4mw7xIZRoVqXRE-Za8-d1qRIL-rNBL_6G1bqLeYE&s=10"
    ],
    fun_facts: [
      "Live further south than any other mammal on Earth.",
      "Use their teeth to grind breathing holes in the ice.",
      "Capable of producing over 30 distinct underwater vocalization types.",
      "High myoglobin levels allow for massive oxygen storage in muscles.",
      "Prefer to hunt alone despite congregating near ice holes."
    ]
  },
  {
    scientific_name: "Halichoerus grypus",
    common_name: "Grey seal",
    images: [
      "https://cdn.oceanwide-expeditions.com/media-dynamic/cache/widen_1600/media/default/0001/37/3419ea40b6debf9bcac5d5bb798129a174eec182.jpeg", "https://www.nature.scot/sites/default/files/styles/max_1300x1300/public/2017-07/Seal-D12822.jpg?itok=p_B0TOPc"
    ],
    fun_facts: [
      "Scientific name means 'hook-nosed sea pig'.",
      "Pups are born with white, non-waterproof fur called lanugo.",
      "Females can live up to 35 years, outliving males by a decade.",
      "Known for 'bottling'—sleeping vertically in the water like a cork.",
      "Have distinct parallel nostrils compared to the V-shape of Harbor seals."
    ]
  },
  {
    scientific_name: "Lobodon carcinophagus",
    common_name: "Crabeater seal",
    images: [
      "https://www.chimuadventures.com/sites/default/files/inline-images/shutterstock_82734571-1024x679_0.jpg", "https://cdn.oceanwide-expeditions.com/media-dynamic/cache/widen_1600/media/default/0001/05/e2742c11a4c997ff5b7d539fea92e278e92bb6a5.jpeg"
    ],
    fun_facts: [
      "Rarely eat crabs; 95% of their diet is Antarctic krill.",
      "Have multi-lobed teeth that act as a sieve for straining krill.",
      "Considered the most numerous seal species in the world.",
      "Can reach speeds of 25 km/h across the ice.",
      "Most adults carry scars from failed Leopard seal attacks."
    ]
  },
  {
    scientific_name: "Phoca vitulina",
    common_name: "Harbor seal",
    images: [
      "https://sealconservancy.org/images/HarborSeal4.jpg", "https://lazoo.org/wp-content/uploads/2023/05/Harbor-Seal-Pup-Male-Uncrop-JEP_1198.jpg", "https://www.montereybayaquarium.org/globalassets/mba/images/animals/marine-mammals/harbor-seals-mam020.jpg?format=jpeg&quality=60"
    ],
    fun_facts: [
      "Often stay in the same local area for their entire lives.",
      "Nostrils form a distinct 'V' shape when viewed from the front.",
      "Pups are precocial and can often swim immediately after birth.",
      "Whiskers can detect fish vibrations from 180 meters away.",
      "Can drop their heart rate from 100 to 5 beats per minute while diving."
    ]
  },
  {
    scientific_name: "Pusa hispida",
    common_name: "Ringed seal",
    images: [
      "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTfhMIiZyKUDI3TlaJejeSQkWpRyWksevpIhw&s", "https://www.earthrangers.com/EN/CA/wp-content/uploads/RingedSeal_FeaturedImage.jpg"
    ],
    fun_facts: [
      "Smallest and most common seal species in the Arctic.",
      "Dig subnivean lairs under the snow to protect pups from predators.",
      "Primary prey for polar bears, who sniff out their snow dens.",
      "Use heavy claws to maintain breathing holes in ice 2 meters thick.",
      "Generally solitary and avoid contact with other seals."
    ]
  },
  {
    scientific_name: "Erignathus barbatus",
    common_name: "Bearded seal",
    images: [
      "https://www.biologicaldiversity.org/assets/img/species/mammals/BeardedSealFlickr_foilistpeter.jpg", "https://cdn.oceanwide-expeditions.com/media-dynamic/cache/widen_1600/v2-gallery_media/media608166852f3a9746232103.jpg"
    ],
    fun_facts: [
      "Named for their thick, bushy whiskers that curl when dry.",
      "Benthic feeders that use whiskers to find prey on the sea floor.",
      "Males perform long, musical 'trills' heard for miles underwater.",
      "Possess unique, square-shaped foreflippers with thick nails.",
      "Skin was traditionally used by Inuit for waterproof boot soles."
    ]
  },
  {
    scientific_name: "Hydrurga leptonyx",
    common_name: "Leopard seal",
    images: [
      "https://www.voyagers.travel/_ipx/w_2400&f_webp&q_85/google/travel-web-app-1.appspot.com/flamelink/media/Leopard%20Seal%20-%20Canva%20-%20Gerald%20%20Corsi.jpg%3Falt=media", "https://www.nhm.ac.uk/content/dam/nhm-www/discover/leopard-seals/leopard-seal-close-up-two-column.jpg"
    ],
    fun_facts: [
      "Only seal known to regularly hunt other warm-blooded prey.",
      "Jaws can unhinge to 160 degrees to grip large prey.",
      "Possess both predatory teeth and sieving teeth for krill.",
      "Distinctive reptilian appearance with a massive, flattened head.",
      "Fiercely solitary and highly aggressive toward other seals."
    ]
  },
  {
    scientific_name: "Mirounga angustirostris",
    common_name: "Northern elephant seal",
    images: [
      "https://www.fisheries.noaa.gov/s3//styles/inline_field_thumbnail/s3/2025-03/ESeal_RoxanneBeltran_UCSC_OceanSentinelWebstory.jpg?h=adbb760b&amp;itok=uKBLYLkW", "https://www.fisheries.noaa.gov/s3//styles/full_width/s3/dam-migration/750x500-northern-elephant-seals.png?itok=nlcRo6lX"
    ],
    fun_facts: [
      "Recovered from a population of just 20 in the late 1800s.",
      "Males possess a large, inflatable proboscis used for roaring.",
      "Undergo a 'catastrophic molt' where they shed skin and hair at once.",
      "Migrate up to 20,000 km annually across the North Pacific.",
      "Take 'drifting' power naps while sinking deep into the ocean."
    ]
  }
]

export default sealFacts