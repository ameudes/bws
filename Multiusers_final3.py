import streamlit as st
import pandas as pd
import json
import os
import itertools
import random
import time 
from datetime import datetime

#import gspread
#from gspread_dataframe import set_with_dataframe
#from google.oauth2.service_account import Credentials
#from pydrive.auth import GoogleAuth
#from pydrive.drive import GoogleDrive
#from google.oauth2 import service_account


#Principale modifs :  Génération aléatoire constante des séquences d'option pour chaque participants, choix de la séquence à appliquer et mise à jour du json dès le début, Mise à jour du json à la fin après soumission
#Ajout des éléments dans un session_state pour éviter un rerun à chaque selection du st.radio qui modifie tout.
#Ajout de l'envoi vers google sheet
#Prise en compte de st.secret
#Ajout du requirement avec pipreqs --use-local --force
#Ajout des labels de chaque choix
#Modification du welcome page
#Rectification Erreur au niveau de l'indexation :  st.session_state.lists = liste[selected] revu pour st.session_state.lists = liste[selected-1]
#Rajout du modulo pour roter lorsque les 55 sont passés ;  une nouvelle clé dans subset group (index), avec une valeur initiale 0 |  Modif de la fonction read_susbsetgroup pour prendre en compte la clé de la liste à lire   | modification de update pour rajouter le prochain indice à utiliser , plus besoin de remaining
#Insertion d'un attention checker au milieu :  réajustement des index et du progress bar 
#Capture du nom du répondant à l'entrée: Welcome page
#Modification du code de génération et mise à jour pour le faire après remplissage du nom afin d'éviter des incrémentations excessive de l'index
# Switch de la connexion Google sheet a Neon 
# Rajout du date pour suivre les remplissages à la va vite


#Quelques fonctions clés
def read_subsetgroup(key): # Fonction pour lire les indices depuis le fichier JSON
    if os.path.exists("subsetgroup.json"):
        with open("subsetgroup.json", "r") as f:
            data = json.load(f)
            return data.get(key)

def update_subsetgroup(indice): #Fonction pour rajouter le prochain indice à utiliser (il s'agit du c_ind utilisé plus bas, on rajoute dans index )
    with open("subsetgroup.json","r") as f:
        data = json.load(f)
        data["index"].append(indice)    
    with open("subsetgroup.json", "w") as o:
        json.dump(data, o)
                
def write_subsetgroup(indice): # Fonction pour écrire les indices terminés dans le fichier JSON
    with open("subsetgroup.json","r") as f:
        data = json.load(f)
        data["end"].append(indice)
      
    with open("subsetgroup.json", "w") as o:
        json.dump(data, o)

def inserer (df): # Fonction pour envoyer les données vers Neon
    
    #Mise en place de la connexion à la base de donnée
    host=st.secrets.db_credentials.host
    username=st.secrets.db_credentials.username
    password=st.secrets.db_credentials.password
    db=st.secrets.db_credentials.database
    from sqlalchemy import URL, create_engine
    connection_string = URL.create('postgresql',username=username,password=password,host=host,database=db)
    engine = create_engine(connection_string, connect_args={'sslmode':'require'})
    
    
    #Définition de class Test pour l'insertion des données
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import Column, String,Table, Column, Integer, Float, MetaData,update
    from sqlalchemy.orm import declarative_base, relationship
    from sqlalchemy.engine import reflection
    Base = declarative_base()
    Session = sessionmaker(bind=engine)
    session = Session()

    class Test(Base):
        __tablename__ = 'bws'

        id = Column(Integer, primary_key=True)
        name=Column(String(100))
        participant =Column(Integer)
        set = Column(Integer)
        most_imp=Column(String(100))
        least_imp=Column(String(100))
        DateTime=Column(String(60))
        
    try:
        for _, row in df.iterrows():
            
            record = Test(
                name=row["Name"],
                participant=row["Participant"],
                set=row["Subset"],
                most_imp=row["Most Important"],
                least_imp=row["Least Important"],
                DateTime=row["DateTime"]
            )
            session.add(record)
            session.commit()
        st.success("✅ Données enregistrées avec succès.")
    except Exception as e:
        session.rollback()
        st.error(f"Erreur lors de l'insertion : {e}")
    finally:
        session.close()




#Multipage survey begin
# Initialize session state variables if they don't exist
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if 'responses' not in st.session_state:
    st.session_state.responses = []

#Welcome page to introduce participants
if 'start' not in st.session_state:
    st.session_state.start = False


##### Default / Welcome Page 
if not st.session_state.start:
    st.title("Bienvenue")
    st.write("""
        Ce questionnaire explore l'importance de divers aspects des données ouvertes (open data) dans un contexte de participation citoyenne.  
        
        **La participation citoyenne** désigne l'engagement des citoyens dans les processus décisionnels publics (ex: budget participatif, assemblée citoyenne, etc).  
        
        **Les données ouvertes** permettent d'accéder librement à des informations publiques essentielles pour renforcer la transparence et l'implication citoyenne.  

        Dans ce questionnaire, vous êtes invités à choisir, pour chaque groupe de caractéristiques, l’aspect le plus important et celui le moins important dans le cadre d'une participation citoyenne. Toutes les données recueillies seront utilisées uniquement pour les besoins de cette recherche.
        
        **Durée estimée** : 7 minutes
    """)
    
    name= st.text_input("Débuter avec votre nom et prénom:")
    
    if st.button("Débuter"):
        if name: 
            st.session_state.username=name   
            st.session_state.start = True
            
            ######NEW CODE POUR REGLER L'INDEX QUI EVOLUE TROP##############
            #Stockage de la liste de question spécifique au user dans un session_state
            if 'list_user' not in st.session_state:
                
                # Recuperation de l'indice identifiant l'odre du répondant actuel (Le dernier dans la liste)
                c_ind = read_subsetgroup("index") [-1]
                #En fonction de l'indice précédent, définition du set d'option à lui afficher, on prends le modulo pour assurer une rotation si on passe le cap des 55
                selected = c_ind % 55  
                #Mise à jour de l'indice pour le prochain répondant 
                update_subsetgroup(c_ind+1)  
                    
                #Lecture du fichier contenant les listes des séquence d'options (lists.json)
                with open("lists.json", "r") as f:
                        liste = json.load(f)
                        st.session_state.lists = liste[selected] #Stocker dans la session la séquence de questions (options) associée à l'indice sélectionné
                        st.session_state.selected=selected #Stocker dans la session l'indice retenu pour le user
                        st.session_state.participant=c_ind #Stocker le numéro du participant 
                
                #Lecture du fichier contenant la liste des labels
                with open ("labels.json", "r") as l:
                    lab= json.load(l)
                    st.session_state.labels = lab[selected]
                    
                    
                st.session_state.list_user = True



            
            ######FIN CODE POUR REGLER L'INDEX QUI EVOLUE TROP##############
            
            
            
            
            st.experimental_rerun()
        else: 
            st.warning("Merci d’entrer votre nom ainsi que votre prénom avant de commencer.")
else : 


    ####### Actual SURVEY
    
    # Utilisation de la séquence sélectionnée pour les choices
    lists = st.session_state.lists
    # Utilisation de la séquence sélectionnée pour les labels
    labels=st.session_state.labels
    
    # Check if we have completed all lists
    if st.session_state.current_index > len(lists): # Because of attention checker on retourne à la condition st.session_state.current_index > len(lists)
        st.title("Merci de votre participation !")
        
        with st.spinner("Envoi des données... Veuillez patienter quelques secondes"):
            time.sleep(3)  
        st.write("Enregistrement en cours ... Veuillez patienter quelques secondes!")
        
        #Send the data to Google sheet
        df = pd.DataFrame(st.session_state.responses)
        inserer(df)    
        #write_subsetgroup(st.session_state.selected) # Add the selected indice to end in subsetgroup.json
        
        st.write("Vos réponses ont été enregistrées")

    else:
        
        #Start differencing to insert an attention checker at the middle of the questions
        
        if st.session_state.current_index < 9:
            
            st.markdown("## PREMIERE PARTIE")
            st.title(f"Set {st.session_state.current_index + 1} sur {len(lists)}")
            # Get the current list of options
            data = lists[st.session_state.current_index]
            #Get the current list of labels
            choices=labels[st.session_state.current_index]
            
        elif  st.session_state.current_index > 9 :
              
            st.markdown("## SECONDE PARTIE")
            st.title(f"Set {st.session_state.current_index} sur {len(lists)}") #On débute à partir de 10 à cause de l'attention checker donc plus besoin d'incrémenter de 1
            # Get the current list of options
            data = lists[st.session_state.current_index-1] #-1 pour réafficher le previous qu'on a pas encore fait et ainsi de suite
            #Get the current list of labels
            choices=labels[st.session_state.current_index-1]

        elif  st.session_state.current_index == 9 : ### Inserer l'attention checker ici
            
            # Get the previous set [st.session_state.current_index == 8]
            data = lists[st.session_state.current_index-1]
            #Get the current list of labels
            choices=labels[st.session_state.current_index-1]
                  
            st.markdown("## Petite étape d’attention")
            st.markdown(  f"#### 🚨 Pour cette question merci de cocher: \"{choices[2]}\" comme plus important et \"{choices[0]}\" comme moins important.")
        
          
        
        
        #######Here we put the code for a single page survey     

        # --- Custom CSS for table styling ---
        # This CSS defines classes for table headers and cells with visible borders.
        st.markdown(
            """
            <style>
            /* Table header style */
            .table-header {
                font-weight: bold;
                background-color: #f1f1f1;
                border: 1px solid black;
                padding: 10px;
                text-align: center;
            }
            /* Table cell style */
            .table-cell {
                border: 1px solid black;
                padding: 10px;
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # --- App Title ---
        #st.title("")
        st.markdown("Mentionner dans un contexte de participation citoyenne :<br>🟩 l’aspect que vous trouvez le plus important,<br>🟥 celui que vous jugez le moins important.", unsafe_allow_html=True)



        # --- Create the table header row using st.columns ---
        #header_cols = st.columns([1.1, 2.8, 1.1])
        #with header_cols[0]:
        #    st.markdown("<div class='table-header' style='color: red;'>Moins important</div>", unsafe_allow_html=True)
        #with header_cols[1]:
        #    st.markdown("<div class='table-header'>Dimension</div>", unsafe_allow_html=True)
        #with header_cols[2]:
        #    st.markdown("<div class='table-header' style='color: green;'>Plus important</div>", unsafe_allow_html=True)

        # --- List to store responses for each row # We replace choices by the current list of labels at line 140
        #choices=[1,2,3]

        cols = st.columns([1.1, 2.8, 1.1])

        #First, here we add both default key (default=0) to st.radio associated to most_choice and least_choice, in order to force equality and have a checking on whether the same dimension is selected as most and least important 
        #Here to avoid the fact that the previous state choices are still chown in the current state, we add the current session index to every st.radio key for most important and least important
        #Now responsive part we redesign the tables, we no more use the table header style 
        #We add a welcome page


        # In the right cell, we put a Streamlit radio widget for "Most Important" selection.
        with cols[2]:
            # Wrap the radio widget in a div that is styled to align its content at the top.
            
            
            st.markdown(
                """
                <div style="display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
                    <style>
                        .stRadio [role="radiogroup"] {
                            align-items: left;
                        }
                    </style>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div style='color: green; text-align: left;'><strong>Plus important</strong></div>", unsafe_allow_html=True)
            most_choice = st.radio(" ", options=choices, key=f"most_{st.session_state.current_index}", index=0)
            st.markdown("</div>", unsafe_allow_html=True)
            
        # In the left cell we do the same 
        with cols[0]:
            # Wrap the radio widget in a div that is styled to align its content at the top.
            st.markdown(
                """
                <div style="display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
                    <style>
                        .stRadio [role="radiogroup"] {
                            align-items: left;
                        }
                    </style>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div style='color: red; text-align: left;'><strong>Moins important</strong></div>", unsafe_allow_html=True)
            least_choice = st.radio(" ", options=choices, key=f"least_{st.session_state.current_index}",index=0)
            st.markdown("</div>", unsafe_allow_html=True)    
                    
        # --- Create one table row for each survey question ---
        for i,row in enumerate(data):       
            # In the center cell, display the list of options
            with cols[1]:
                # Create a numbered list with the row number using the 'start' attribute
                cell_text = "".join([f"<li> <strong>{choices[i]}</strong>: {row}</li>"])  # on rajoute le label dans le display de l'option' 
                st.markdown(
                    f"<div class='table-cell' style='text-align: left;'><ol start='{i+1}'>{cell_text}</ol></div>",
                    unsafe_allow_html=True)  
                        
        #######End of the single page survey code 
        
        
        
             
        # Button to submit the current response and move to the next list
        if st.button("Suivant", key=f"next"):
            if most_choice==least_choice:
                st.error('Le moins important et le plus important doivent êtres différents', icon="🚨") 
            else:    
            # Save the current response (list number and selected option)
                
                
                st.session_state.responses.append({
                    "Name": st.session_state.username,
                    "Participant": st.session_state.participant, #stockage du numéro du participant
                    "Subset": st.session_state.current_index + 1,
                    "Most Important": most_choice,
                    "Least Important": least_choice,
                    "DateTime": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                })
                # Move to the next list
                st.session_state.current_index += 1
                
                # Rerun the app so that the new task appears
                st.experimental_rerun()

    #progression bar            
    st.progress(int((st.session_state.current_index/(len(lists)+1))*100))