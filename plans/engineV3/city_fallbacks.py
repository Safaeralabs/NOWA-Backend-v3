"""
Static fallbacks for City DNA when LLM is unavailable.

Covers top 15 cities with curated local knowledge.
Used as fallback in llm.py::get_city_dna()
"""

DEFAULT_FALLBACK = {
    "city": "Unknown",
    "language": "es",
    "food_typicals": [],
    "drink_typicals": [],
    "local_keywords": [],
    "negative_keywords": ["tourist_trap", "overpriced"],
    "etiquette": ["Tip 10-15% if service was good"],
    "neighborhood_hints": []
}

CITY_FALLBACKS = {
    # ========== GERMANY ==========
    "Munich": {
        "city": "Munich",
        "language": "es",
        "food_typicals": [
            {
                "name": "Weißwurst",
                "note": "Salchicha blanca bávara tradicional, solo se come antes del mediodía",
                "when": ["morning", "brunch"],
                "how_to_order": "Si ves Weißwurst en el menú antes de las 12pm, pídelo con mostaza dulce"
            },
            {
                "name": "Schweinshaxe",
                "note": "Codillo de cerdo asado, crujiente por fuera y jugoso por dentro",
                "when": ["midday", "evening"],
                "how_to_order": "Pregunta si tienen Schweinshaxe con Knödel (albóndigas de papa)"
            },
            {
                "name": "Bretzel",
                "note": "Pretzel gigante típico de Baviera",
                "when": ["morning", "afternoon"],
                "how_to_order": "Pide Bretzel con Obatzda (queso cremoso bávaro con especias)"
            },
            {
                "name": "Leberkäse",
                "note": "Pastel de carne tipo bologna, servido caliente",
                "when": ["midday"],
                "how_to_order": "Si ves Leberkäse, pídelo en semmel (pan) con mostaza"
            },
            {
                "name": "Kaiserschmarrn",
                "note": "Panqueque dulce desmigajado, postre tradicional",
                "when": ["afternoon", "evening"],
                "how_to_order": "Típico de postre, pídelo con compota de ciruelas"
            }
        ],
        "drink_typicals": [
            {
                "name": "Maß",
                "note": "1 litro de cerveza, medida tradicional en cervecerías",
                "when": ["midday", "evening"],
                "how_to_order": "Pide una Maß Helles (clara) o Dunkel (oscura)"
            },
            {
                "name": "Radler",
                "note": "Cerveza mezclada con limonada, refrescante",
                "when": ["afternoon"],
                "how_to_order": "Perfecto para días calurosos, pide Radler en terrazas"
            },
            {
                "name": "Apfelschorle",
                "note": "Jugo de manzana con agua con gas, bebida sin alcohol",
                "when": ["morning", "afternoon"],
                "how_to_order": "Bebida típica alemana, pregunta por Apfelschorle"
            },
            {
                "name": "Schnapps",
                "note": "Aguardiente de frutas, digestivo tradicional",
                "when": ["evening", "late"],
                "how_to_order": "Pídelo después de la cena como digestivo"
            }
        ],
        "local_keywords": ["biergarten", "bavarian", "traditional", "brewery", "wirtshaus"],
        "negative_keywords": ["tourist_trap", "hofbräuhaus_overpriced"],
        "etiquette": [
            "En Biergarten (jardines de cerveza), es normal compartir mesa si está lleno",
            "Saluda con 'Grüß Gott' en vez de 'Hallo' para sonar más local",
            "Los domingos la mayoría de tiendas cierran, planifica con anticipación",
            "No agites tus brazos para llamar al mesero, usa contacto visual"
        ],
        "neighborhood_hints": [
            {
                "name": "Schwabing",
                "vibe": ["artsy", "student", "lively"],
                "best_for": ["nightlife", "cafes", "shopping"]
            },
            {
                "name": "Glockenbachviertel",
                "vibe": ["hip", "diverse", "lgbtq-friendly"],
                "best_for": ["bars", "restaurants", "nightlife"]
            },
            {
                "name": "Maxvorstadt",
                "vibe": ["cultural", "museum", "university"],
                "best_for": ["museums", "galleries", "cafes"]
            }
        ]
    },

    "Berlin": {
        "city": "Berlin",
        "language": "es",
        "food_typicals": [
            {
                "name": "Currywurst",
                "note": "Salchicha con curry ketchup, icónico de Berlín",
                "when": ["midday", "evening", "late"],
                "how_to_order": "Si ves Currywurst, pídelo con papas fritas"
            },
            {
                "name": "Döner Kebab",
                "note": "Kebab turco, Berlin tiene los mejores",
                "when": ["midday", "evening", "late"],
                "how_to_order": "Pregunta si hacen döner fresco, con todas las salsas"
            },
            {
                "name": "Berliner Pfannkuchen",
                "note": "Donut relleno de mermelada",
                "when": ["morning", "afternoon"],
                "how_to_order": "En panaderías, pide Berliner (no llames Berliner a la gente!)"
            }
        ],
        "drink_typicals": [
            {
                "name": "Berliner Weiße",
                "note": "Cerveza ácida con jarabe de frambuesa o woodruff",
                "when": ["afternoon", "evening"],
                "how_to_order": "Pide Berliner Weiße mit Schuss (con jarabe)"
            },
            {
                "name": "Club-Mate",
                "note": "Bebida energética de yerba mate, culto en Berlín",
                "when": ["afternoon", "evening", "late"],
                "how_to_order": "Típica en bares alternativos, pregunta por Club-Mate"
            }
        ],
        "local_keywords": ["street_food", "kebab", "alternative", "techno", "kreuzberg"],
        "negative_keywords": ["checkpoint_charlie_area"],
        "etiquette": [
            "Berlín es muy informal, no te vistas demasiado elegante",
            "Los bares de techno tienen door policy estricta (no fotos, no turistas obvios)",
            "Recicla tu basura, los berlineses son serios con esto"
        ]
    },

    # ========== SPAIN ==========
    "Madrid": {
        "city": "Madrid",
        "language": "es",
        "food_typicals": [
            {
                "name": "Bocadillo de Calamares",
                "note": "Bocadillo de calamares fritos, clásico madrileño",
                "when": ["midday", "afternoon"],
                "how_to_order": "Evita Plaza Mayor (turístico), busca bares locales para mejor calidad"
            },
            {
                "name": "Cocido Madrileño",
                "note": "Estofado de garbanzos con carne y verduras, plato invernal",
                "when": ["midday"],
                "how_to_order": "Si ves Cocido en el menú del día (típico jueves), pídelo"
            },
            {
                "name": "Churros con Chocolate",
                "note": "Churros crujientes con chocolate espeso para mojar",
                "when": ["morning", "late"],
                "how_to_order": "Tradicional para desayuno o después de salir de fiesta (3-5am)"
            },
            {
                "name": "Huevos Rotos",
                "note": "Huevos fritos sobre papas fritas, se rompen al servir",
                "when": ["midday", "evening"],
                "how_to_order": "Pídelo con jamón ibérico, es un clásico madrileño"
            }
        ],
        "drink_typicals": [
            {
                "name": "Caña",
                "note": "Cerveza pequeña de barril (200ml), típica en bares",
                "when": ["afternoon", "evening"],
                "how_to_order": "Simplemente pide 'una caña' en cualquier bar"
            },
            {
                "name": "Tinto de Verano",
                "note": "Vino tinto con gaseosa, más ligero que sangría",
                "when": ["afternoon", "evening"],
                "how_to_order": "Refrescante en verano, pregunta por tinto de verano"
            },
            {
                "name": "Vermut",
                "note": "Vermut de grifo, tradición del aperitivo",
                "when": ["midday"],
                "how_to_order": "Típico el domingo antes de comer, pide vermut de grifo"
            }
        ],
        "local_keywords": ["tapas", "taberna", "castizo", "mercado", "terraza"],
        "negative_keywords": ["tourist_menu", "sol_area", "plaza_mayor_restaurants"],
        "etiquette": [
            "Cena tarde: restaurantes se llenan después de las 21:00-22:00",
            "Es normal ir de tapas (tapear) saltando de bar en bar",
            "En mercados como San Miguel, los precios son muy turísticos",
            "Saluda con dos besos (izquierda primero)"
        ],
        "neighborhood_hints": [
            {
                "name": "Malasaña",
                "vibe": ["hipster", "alternative", "young"],
                "best_for": ["nightlife", "vintage shopping", "cafes"]
            },
            {
                "name": "La Latina",
                "vibe": ["traditional", "tapas", "lively"],
                "best_for": ["tapas bars", "sunday vermouth"]
            }
        ]
    },

    "Barcelona": {
        "city": "Barcelona",
        "language": "es",
        "food_typicals": [
            {
                "name": "Pan con Tomate",
                "note": "Pan tostado con tomate rallado, aceite y sal",
                "when": ["morning", "midday"],
                "how_to_order": "Si ves 'pa amb tomàquet', pídelo - es básico catalán para acompañar"
            },
            {
                "name": "Patatas Bravas",
                "note": "Papas fritas con salsa brava y alioli",
                "when": ["afternoon", "evening"],
                "how_to_order": "Pregunta por bravas - cada bar tiene su receta secreta"
            },
            {
                "name": "Crema Catalana",
                "note": "Postre similar a crème brûlée pero más ligero",
                "when": ["afternoon", "evening"],
                "how_to_order": "Postre típico catalán, pídelo después de la comida"
            },
            {
                "name": "Butifarra",
                "note": "Salchicha catalana típica",
                "when": ["midday", "evening"],
                "how_to_order": "Si ves butifarra con mongetes (judías blancas), pídelo"
            }
        ],
        "drink_typicals": [
            {
                "name": "Vermut",
                "note": "Vermut artesanal catalán, tradición del aperitivo",
                "when": ["midday", "afternoon"],
                "how_to_order": "Típico antes de comer, pide vermut de grifo (del barril)"
            },
            {
                "name": "Cava",
                "note": "Espumoso catalán, similar a champagne",
                "when": ["evening"],
                "how_to_order": "Producido localmente en Penedès, pregunta por cava catalán"
            },
            {
                "name": "Carajillo",
                "note": "Café con brandy/licor, digestivo típico",
                "when": ["evening"],
                "how_to_order": "Después de comer, pide un carajillo"
            }
        ],
        "local_keywords": ["catalan", "vermuteria", "bodega", "mercat", "rambla_alternatives"],
        "negative_keywords": ["las_ramblas_restaurants", "tourist_menu", "sagrada_familia_area"],
        "etiquette": [
            "Muchos locales hablan catalán primero, pero todos entienden español",
            "Evita Las Ramblas para comer - zonas como Gràcia o Poblenou son mejores",
            "Siesta: algunos negocios cierran 14:00-17:00",
            "Catalanes son orgullosos de su cultura, respeta sus tradiciones"
        ],
        "neighborhood_hints": [
            {
                "name": "Gràcia",
                "vibe": ["bohemian", "local", "artistic"],
                "best_for": ["authentic dining", "small plazas", "local bars"]
            },
            {
                "name": "El Born",
                "vibe": ["trendy", "historic", "nightlife"],
                "best_for": ["tapas", "cocktail bars", "shopping"]
            }
        ]
    },

    # ========== FRANCE ==========
    "Paris": {
        "city": "Paris",
        "language": "es",
        "food_typicals": [
            {
                "name": "Croissant",
                "note": "Croissant mantequilloso, mejor en panaderías artesanales",
                "when": ["morning"],
                "how_to_order": "Pide 'un croissant au beurre' (con mantequilla), evita los industriales"
            },
            {
                "name": "Croque-Monsieur",
                "note": "Sándwich caliente de jamón y queso gratinado",
                "when": ["midday"],
                "how_to_order": "Clásico de bistrot, pídelo para almuerzo rápido"
            },
            {
                "name": "Steak Frites",
                "note": "Filete con papas fritas, simple pero delicioso",
                "when": ["midday", "evening"],
                "how_to_order": "En bistrot, pide el steak a punto (à point) con mantequilla de hierbas"
            },
            {
                "name": "Crêpe",
                "note": "Crepa dulce o salada, típica parisina",
                "when": ["afternoon", "evening"],
                "how_to_order": "Dulce con Nutella, salada (galette) con huevo y queso"
            }
        ],
        "drink_typicals": [
            {
                "name": "Café",
                "note": "Espresso corto, se toma parado en la barra",
                "when": ["morning", "afternoon"],
                "how_to_order": "Pide 'un café' (espresso) o 'un café crème' (con leche)"
            },
            {
                "name": "Vin Rouge/Blanc",
                "note": "Vino tinto o blanco, calidad excelente",
                "when": ["midday", "evening"],
                "how_to_order": "Pide una copa (un verre) o botella, pregunta recomendación del día"
            },
            {
                "name": "Pastis",
                "note": "Licor anisado típico francés, aperitivo",
                "when": ["afternoon", "evening"],
                "how_to_order": "Se mezcla con agua, pídelo como aperitivo"
            }
        ],
        "local_keywords": ["bistrot", "boulangerie", "marché", "terrasse", "quartier"],
        "negative_keywords": ["champs_elysees_restaurants", "tourist_trap_latin_quarter"],
        "etiquette": [
            "Saluda siempre con 'Bonjour' al entrar a una tienda",
            "Los parisinos valoran la cortesía, sé educado",
            "Propinas no son obligatorias (servicio incluido), pero redondea la cuenta",
            "No hables fuerte en restaurantes, los franceses valoran la discreción"
        ]
    },

    # ========== UK ==========
    "London": {
        "city": "London",
        "language": "es",
        "food_typicals": [
            {
                "name": "Fish and Chips",
                "note": "Pescado frito con papas fritas, clásico británico",
                "when": ["midday", "evening"],
                "how_to_order": "Pídelo en un pub tradicional con guisantes machacados (mushy peas)"
            },
            {
                "name": "Full English Breakfast",
                "note": "Desayuno completo: huevos, bacon, salchicha, frijoles, tomate",
                "when": ["morning"],
                "how_to_order": "En cafés tradicionales, pide el 'Full English' completo"
            },
            {
                "name": "Sunday Roast",
                "note": "Asado dominical con verduras y Yorkshire pudding",
                "when": ["midday"],
                "how_to_order": "Típico los domingos en pubs, reserva con anticipación"
            },
            {
                "name": "Pie",
                "note": "Pastel salado (carne, pollo, vegetales)",
                "when": ["midday", "evening"],
                "how_to_order": "En pubs, pregunta por el pie del día"
            }
        ],
        "drink_typicals": [
            {
                "name": "Pint",
                "note": "Pinta de cerveza (568ml), ale o lager",
                "when": ["afternoon", "evening"],
                "how_to_order": "Pide 'a pint of...' en el bar (no hay servicio en mesa para bebidas)"
            },
            {
                "name": "Gin & Tonic",
                "note": "Gin tonic con pepino, tradición londinense",
                "when": ["evening"],
                "how_to_order": "Londres tiene gin bars especializados, pregunta por gin local"
            },
            {
                "name": "Tea",
                "note": "Té negro con leche, bebida nacional",
                "when": ["afternoon"],
                "how_to_order": "Afternoon tea (3-5pm) con scones en hoteles o cafés elegantes"
            }
        ],
        "local_keywords": ["pub", "market", "borough", "ale", "traditional"],
        "negative_keywords": ["leicester_square_restaurants", "oxford_street_dining"],
        "etiquette": [
            "Haz fila (queue) siempre, los británicos son estrictos con esto",
            "En el pub, ordena en la barra y paga inmediatamente",
            "Propina 10-12.5% en restaurantes si el servicio no está incluido",
            "Di 'please' y 'thank you' constantemente"
        ]
    },

    # ========== ITALY ==========
    "Rome": {
        "city": "Rome",
        "language": "es",
        "food_typicals": [
            {
                "name": "Carbonara",
                "note": "Pasta con huevo, guanciale, pecorino, pimienta negra",
                "when": ["midday", "evening"],
                "how_to_order": "La auténtica NO lleva crema, si la ves con crema es turística"
            },
            {
                "name": "Cacio e Pepe",
                "note": "Pasta con queso pecorino y pimienta negra, simple pero perfecta",
                "when": ["midday", "evening"],
                "how_to_order": "Plato romano tradicional, pídelo en trattorie locales"
            },
            {
                "name": "Supplì",
                "note": "Bola de arroz frita con mozzarella derretida dentro",
                "when": ["afternoon", "evening"],
                "how_to_order": "Snack típico romano, cómelo caliente al salir de la fritura"
            },
            {
                "name": "Gelato",
                "note": "Helado artesanal italiano",
                "when": ["afternoon", "evening"],
                "how_to_order": "Evita colores muy brillantes (artificial), busca gelaterias artesanales"
            }
        ],
        "drink_typicals": [
            {
                "name": "Espresso",
                "note": "Café corto, se toma parado en la barra",
                "when": ["morning", "afternoon"],
                "how_to_order": "Pide 'un caffè' (espresso), NUNCA cappuccino después de las 11am"
            },
            {
                "name": "Aperol Spritz",
                "note": "Aperitivo con Aperol, prosecco y soda",
                "when": ["evening"],
                "how_to_order": "Típico del aperitivo (6-8pm), pídelo con snacks incluidos"
            },
            {
                "name": "Vino della Casa",
                "note": "Vino de la casa, usualmente bueno y económico",
                "when": ["midday", "evening"],
                "how_to_order": "Pregunta por el vino local de la región (Lazio)"
            }
        ],
        "local_keywords": ["trattoria", "osteria", "romano", "trastevere", "testaccio"],
        "negative_keywords": ["colosseum_area_restaurants", "termini_station_dining"],
        "etiquette": [
            "No pidas cappuccino después de las 11am (los italianos solo lo toman en desayuno)",
            "Coperto (cargo por cubierto) es normal, 1-3€ por persona",
            "No esperes servicio rápido, la comida es un ritual social",
            "Propina no es obligatoria, redondea si gustó el servicio"
        ]
    },

    "Milan": {
        "city": "Milan",
        "language": "es",
        "food_typicals": [
            {
                "name": "Risotto alla Milanese",
                "note": "Risotto con azafrán, cremoso y amarillo",
                "when": ["midday", "evening"],
                "how_to_order": "Plato típico milanés, pídelo como primo piatto"
            },
            {
                "name": "Cotoletta alla Milanese",
                "note": "Chuleta de ternera empanizada, frita en mantequilla",
                "when": ["midday", "evening"],
                "how_to_order": "Similar al Wiener Schnitzel, pero con hueso"
            },
            {
                "name": "Panettone",
                "note": "Pan dulce con frutas confitadas, típico navideño",
                "when": ["afternoon"],
                "how_to_order": "Aunque es navideño, lo encuentras todo el año en panaderías"
            }
        ],
        "drink_typicals": [
            {
                "name": "Negroni",
                "note": "Cocktail con gin, Campari y vermut",
                "when": ["evening"],
                "how_to_order": "Milán es la ciudad del aperitivo, pídelo a las 6-7pm"
            },
            {
                "name": "Caffè",
                "note": "Espresso, Milán toma café muy en serio",
                "when": ["morning", "afternoon"],
                "how_to_order": "Párate en la barra, tómalo rápido como los milaneses"
            }
        ],
        "local_keywords": ["aperitivo", "milanese", "fashion", "design", "navigli"],
        "negative_keywords": ["duomo_area_restaurants", "tourist_trap"],
        "etiquette": [
            "Milán es la ciudad más europea de Italia, más formal que Roma",
            "Aperitivo (6-8pm): paga una bebida, snacks buffet incluidos",
            "Vístete bien, los milaneses son fashion-conscious"
        ]
    },

    # ========== NETHERLANDS ==========
    "Amsterdam": {
        "city": "Amsterdam",
        "language": "es",
        "food_typicals": [
            {
                "name": "Stroopwafel",
                "note": "Galleta de caramelo, mejor caliente del mercado",
                "when": ["morning", "afternoon"],
                "how_to_order": "Cómpralo fresco en mercados, ponlo sobre tu café para que se caliente"
            },
            {
                "name": "Bitterballen",
                "note": "Croquetas fritas de carne, típico snack de bar",
                "when": ["evening"],
                "how_to_order": "Pídelo en cualquier bar con cerveza, usa palillo para comer"
            },
            {
                "name": "Haring",
                "note": "Arenque crudo con cebolla y pepinillos",
                "when": ["afternoon"],
                "how_to_order": "En puestos de pescado, cómelo sosteniéndolo por la cola"
            },
            {
                "name": "Poffertjes",
                "note": "Mini panqueques esponjosos con mantequilla y azúcar",
                "when": ["afternoon"],
                "how_to_order": "En mercados o cafés especializados, pídelos frescos"
            }
        ],
        "drink_typicals": [
            {
                "name": "Heineken",
                "note": "Cerveza holandesa, visita la experiencia Heineken",
                "when": ["afternoon", "evening"],
                "how_to_order": "Pide un 'biertje' (cervecita) en cualquier café"
            },
            {
                "name": "Jenever",
                "note": "Gin holandés, precursor del gin",
                "when": ["evening"],
                "how_to_order": "Pruébalo en proeflokalen (bares de degustación tradicionales)"
            },
            {
                "name": "Koffie",
                "note": "Café holandés, fuerte y negro",
                "when": ["morning", "afternoon"],
                "how_to_order": "Los cafés marrones (brown cafes) tienen el mejor ambiente"
            }
        ],
        "local_keywords": ["gezellig", "brown_cafe", "canal", "bike_friendly", "market"],
        "negative_keywords": ["dam_square_restaurants", "red_light_district_dining"],
        "etiquette": [
            "Holandeses son directos, no lo tomes personal",
            "Muévete en bici, pero cuidado con las ciclovías (no camines por ahí)",
            "Coffee shops = marihuana legal, cafés = cafeterías normales",
            "Propina: redondea o deja 5-10%"
        ]
    },

    # ========== PORTUGAL ==========
    "Lisbon": {
        "city": "Lisbon",
        "language": "es",
        "food_typicals": [
            {
                "name": "Pastel de Nata",
                "note": "Tarta de crema, mejor caliente con canela",
                "when": ["morning", "afternoon"],
                "how_to_order": "Los mejores están en Belém, pero pruébalos frescos en cualquier pastelería"
            },
            {
                "name": "Bacalhau",
                "note": "Bacalao, hay 365 formas de prepararlo",
                "when": ["midday", "evening"],
                "how_to_order": "Pregunta por el bacalhau del día, cada restaurante tiene su especialidad"
            },
            {
                "name": "Francesinha",
                "note": "Sándwich cubierto de queso fundido y salsa de tomate/cerveza",
                "when": ["midday", "evening"],
                "how_to_order": "Más típico de Porto, pero lo encuentras en Lisboa también"
            },
            {
                "name": "Sardinhas Assadas",
                "note": "Sardinas asadas, típicas en verano",
                "when": ["midday", "evening"],
                "how_to_order": "Especialmente en junio (festas de Santo António), pídelas frescas"
            }
        ],
        "drink_typicals": [
            {
                "name": "Ginjinha",
                "note": "Licor de cereza ácida, shot típico lisboeta",
                "when": ["afternoon", "evening"],
                "how_to_order": "En barras especializadas, pídelo 'com elas' (con las cerezas dentro)"
            },
            {
                "name": "Vinho Verde",
                "note": "Vino verde portugués, ligero y con burbujas",
                "when": ["midday", "afternoon"],
                "how_to_order": "Refrescante en verano, pídelo bien frío"
            },
            {
                "name": "Café",
                "note": "Espresso portugués, fuerte y aromático",
                "when": ["morning", "afternoon"],
                "how_to_order": "Pide 'uma bica' (espresso) o 'um galão' (café con leche en vaso)"
            }
        ],
        "local_keywords": ["tasco", "cervejaria", "fado", "miradouro", "bairro"],
        "negative_keywords": ["baixa_tourist_restaurants", "rossio_overpriced"],
        "etiquette": [
            "Los portugueses son muy amables y serviciales",
            "Aprende algunas palabras en portugués (no es español)",
            "Propina: 5-10% si el servicio fue bueno",
            "Cuidado con las cuestas, Lisboa tiene muchas colinas"
        ]
    },

    # ========== USA ==========
    "New York": {
        "city": "New York",
        "language": "es",
        "food_typicals": [
            {
                "name": "New York Pizza",
                "note": "Pizza al estilo NY, rebanadas grandes y delgadas",
                "when": ["midday", "evening", "late"],
                "how_to_order": "Pide 'a slice' (rebanada) para probar, dóblala para comerla"
            },
            {
                "name": "Bagel",
                "note": "Panecillo hervido y horneado, con cream cheese y salmón",
                "when": ["morning"],
                "how_to_order": "Pide un bagel con lox (salmón ahumado) y cream cheese"
            },
            {
                "name": "Hot Dog",
                "note": "Perro caliente de carrito callejero, icónico de NYC",
                "when": ["midday", "afternoon"],
                "how_to_order": "De carritos en la calle, pídelo con mostaza y cebolla"
            },
            {
                "name": "Cheesecake",
                "note": "Tarta de queso estilo NY, densa y cremosa",
                "when": ["afternoon", "evening"],
                "how_to_order": "Juniors en Brooklyn es famoso, pero hay muchas opciones"
            }
        ],
        "drink_typicals": [
            {
                "name": "Coffee",
                "note": "Café americano grande, cultura del café para llevar",
                "when": ["morning", "afternoon"],
                "how_to_order": "Deli coffee es más barato que Starbucks y más auténtico"
            },
            {
                "name": "Craft Beer",
                "note": "Cerveza artesanal, Brooklyn tiene muchas cervecerías",
                "when": ["evening"],
                "how_to_order": "Pregunta por cervezas locales de Brooklyn o Queens"
            },
            {
                "name": "Cocktail",
                "note": "Cócteles creativos, NYC tiene bares de clase mundial",
                "when": ["evening"],
                "how_to_order": "Rooftop bars en verano, speakeasies en invierno"
            }
        ],
        "local_keywords": ["deli", "bodega", "brooklyn", "queens", "dive_bar"],
        "negative_keywords": ["times_square_restaurants", "tourist_trap_midtown"],
        "etiquette": [
            "Propina obligatoria: 18-20% en restaurantes, 15-18% en bares",
            "Camina rápido, los neoyorquinos van con prisa",
            "No hables con extraños en el metro (a menos que pidan ayuda)",
            "Taxis: levanta la mano cuando veas luz amarilla encendida"
        ]
    },

    # ========== ASIA ==========
    "Tokyo": {
        "city": "Tokyo",
        "language": "es",
        "food_typicals": [
            {
                "name": "Ramen",
                "note": "Sopa de fideos, hay muchos estilos regionales",
                "when": ["midday", "evening", "late"],
                "how_to_order": "Haz ruido al comer (es de buena educación), termina todo el caldo"
            },
            {
                "name": "Sushi",
                "note": "Sushi fresco, Tokyo tiene el mejor del mundo",
                "when": ["midday", "evening"],
                "how_to_order": "En sushi bars, come de la barra para ver al chef trabajar"
            },
            {
                "name": "Tonkatsu",
                "note": "Chuleta de cerdo empanizada, jugosa y crujiente",
                "when": ["midday", "evening"],
                "how_to_order": "Viene con col rallada, moja en salsa tonkatsu"
            },
            {
                "name": "Okonomiyaki",
                "note": "Panqueque salado japonés con varios ingredientes",
                "when": ["evening"],
                "how_to_order": "En Osaka es más típico, pero lo encuentras en Tokyo también"
            }
        ],
        "drink_typicals": [
            {
                "name": "Sake",
                "note": "Vino de arroz, puede ser frío o caliente",
                "when": ["evening"],
                "how_to_order": "Pregunta al staff si recomienda sake local (jizake)"
            },
            {
                "name": "Matcha",
                "note": "Té verde en polvo, ceremonial o casual",
                "when": ["afternoon"],
                "how_to_order": "En cafés modernos o casas de té tradicionales"
            },
            {
                "name": "Highball",
                "note": "Whisky con soda, muy popular en izakayas",
                "when": ["evening"],
                "how_to_order": "Bebida típica de after-work, refrescante"
            }
        ],
        "local_keywords": ["izakaya", "konbini", "depachika", "standing_bar", "yokocho"],
        "negative_keywords": ["shinjuku_tourist_restaurants", "roppongi_overpriced"],
        "etiquette": [
            "No des propina (se considera ofensivo)",
            "Quítate los zapatos en restaurantes tradicionales",
            "No hables por teléfono en el tren",
            "Haz reverencia leve al saludar y agradecer"
        ]
    },

    "Bangkok": {
        "city": "Bangkok",
        "language": "es",
        "food_typicals": [
            {
                "name": "Pad Thai",
                "note": "Fideos salteados con tamarindo, maní y limón",
                "when": ["midday", "evening"],
                "how_to_order": "De puestos callejeros es más auténtico, ajusta el picante"
            },
            {
                "name": "Tom Yum Goong",
                "note": "Sopa picante y ácida con camarones",
                "when": ["midday", "evening"],
                "how_to_order": "Pídelo 'mai pet' (no picante) si no toleras mucho picante"
            },
            {
                "name": "Som Tam",
                "note": "Ensalada de papaya verde picante",
                "when": ["midday", "afternoon"],
                "how_to_order": "Típico de Isaan (noreste), muy picante - pide menos chiles"
            },
            {
                "name": "Mango Sticky Rice",
                "note": "Postre de mango con arroz glutinoso y leche de coco",
                "when": ["afternoon", "evening"],
                "how_to_order": "Mejor en temporada de mangos (marzo-junio)"
            }
        ],
        "drink_typicals": [
            {
                "name": "Thai Iced Tea",
                "note": "Té tailandés con leche condensada, muy dulce",
                "when": ["afternoon"],
                "how_to_order": "Refrescante con el calor, pide 'cha yen'"
            },
            {
                "name": "Chang Beer",
                "note": "Cerveza tailandesa popular",
                "when": ["evening"],
                "how_to_order": "Típica en street food, pide bien fría"
            },
            {
                "name": "Nam Manao",
                "note": "Limonada tailandesa con sal",
                "when": ["afternoon"],
                "how_to_order": "Refrescante, equilibra dulce-salado-ácido"
            }
        ],
        "local_keywords": ["street_food", "night_market", "boat_noodles", "isaan", "khao_san"],
        "negative_keywords": ["khao_san_road_restaurants", "tourist_trap_riverside"],
        "etiquette": [
            "No toques la cabeza de nadie (es sagrada)",
            "No señales con los pies (es irrespetuoso)",
            "Quítate los zapatos antes de entrar a casas/templos",
            "Respeta las imágenes de la familia real"
        ]
    },
}


def get_city_fallback(city: str) -> dict:
    """
    Get static fallback for a city, or default if not available.
    
    Args:
        city: City name (case-insensitive)
    
    Returns:
        dict: City DNA with food/drink typicals, keywords, etiquette
    """
    city_key = city.strip().title()
    fallback = CITY_FALLBACKS.get(city_key)
    
    if fallback:
        return fallback.copy()
    
    # Return generic fallback
    return DEFAULT_FALLBACK.copy()