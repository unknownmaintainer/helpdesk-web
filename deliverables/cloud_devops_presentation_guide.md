# Presentation & Demo Cheat Sheet: Lead Cloud & DevOps Engineer

Heto ang iyong simpleng gabay para sa presentation at live demo sa panel bilang **Lead Cloud & DevOps Engineer**. Ang naging focus mo ay ang pag-setup ng imprastraktura ng application sa cloud.

---

## Part 1: Ano ang purpose ng iyong role? (Paliwanag sa Madaling Salita)
Kapag tinanong ka ng panel kung ano ang halaga ng DevOps, sabihin mo ito:
1. **Live App (Render Deployment):** Imbes na sa sarili nating computer lang tumatakbo ang website, inilagay ko ito sa cloud (Render PaaS) para ma-access ito ng kahit sino sa internet gamit ang HTTPS at may kasamang SSL padlock (padlock icon sa address bar) para sa data encryption.
2. **PostgreSQL Database:** Inilipat natin ang local file na database (SQLite) papunta sa isang secure cloud database service (PostgreSQL) na kayang mag-handle ng maramihang users nang sabay-sabay nang hindi nasisira ang data.
3. **Cloudinary Integration:** Dahil ang cloud servers (Render) ay nawawalan ng files tuwing nagre-restart o nag-a-update ng code, isinama natin ang Cloudinary. Dito permanente at ligtas na inilalagay ang lahat ng ticket attachments at mga profile pictures ng users.
4. **Environment Variables:** Tinatago natin ang mga master keys at passwords sa labas ng code (sa Render Dashboard) para kahit ma-access ng publiko ang GitHub code, hindi nila mananakaw ang ating databases at Cloudinary keys.

---

## Part 2: Step-by-Step Live Demo sa Browser (Ang Ipakikita at Sasabihin Mo)

*I-share ang iyong screen kung saan nakabukas ang Chrome o Edge browser.*

### Step 1: Ipakita ang Live App at SSL padlock
* **Action (Gawin mo):**
  1. Ipakita ang homepage ng website sa: `https://helpdesk-web.onrender.com/` (o ang inyong live Render link).
  2. I-click ang **padlock (lock) icon** sa kaliwa ng browser address bar para implicit na ipakita na *"Connection is secure"*.
* **Script (Sasabihin mo):**
  > *"Magandang umaga po sa inyong lahat. Ako po ang Lead Cloud & DevOps Engineer ng aming team. Upang buksan ang aming presentation, nais ko pong ipakita na ang aming application ay live at accessible sa internet gamit ang aming Render URL.*
  > 
  > *Gaya po ng inyong nakikita (ituro ang lock icon), ang ating portal ay protektado ng **SSL Certificate**. Ibig sabihin po, ang lahat ng data na ipinapadala ng aming mga users ay encrypted sa transit papunta sa server."*

---

### Step 2: Patunayan ang Cloudinary Cloud Storage (The Attachment Test)
* **Action (Gawin mo):**
  1. Mag-login at pumunta sa kahit anong ticket details na may attachment o pumunta sa profile ng kahit sinong user na may profile picture.
  2. I-right-click ang imahe o attachment file ➔ Piliin ang **`Open image in new tab`** (o *Open link in new tab*).
  3. Ipakita sa panel ang URL sa bagong tab: dapat ay nagsisimula ito sa **`res.cloudinary.com/...`**.
* **Script (Sasabihin mo):**
  > *"Upang patunayan po na gumagana ang ating media storage integration sa cloud, i-open natin ang user profile picture na ito sa bagong tab.*
  > 
  > *Makikita ninyo po sa link sa itaas na ang host nito ay **`res.cloudinary.com`**. Ibig sabihin po, lahat ng in-upload na files ay hindi naitatabi sa local web server kundi sa isang scalable cloud media vault. Ligtas po ang files kahit mag-restart o mag-rebuild ang ating application."*

---

### Step 3: Ipaliwanag kung paano gumagana ang Secure Settings at Git
* **Action (Gawin mo):**
  1. Kung pinapayagan ng panel na magpakita ng settings code, buksan ang **`settings.py`** sa VS Code.
  2. Ipakita ang linya kung saan binabasa ang passwords gamit ang `os.getenv(...)`.
* **Script (Sasabihin mo):**
  > *"Upang masiguro po na hindi mananakaw ang aming databases at passwords, gumamit po tayo ng **Environment Variables**.*
  > 
  > *Sa aming code (ituro ang `os.getenv`), binabasa lang po ng Django ang database link at API keys mula sa server environment tuwing maglo-load ang site. Ang mga active keys ay nakatago sa Render cloud dashboard at kailanman ay hindi isinama sa aming code sa GitHub.*
  > 
  > *Gumamit din po kami ng `.gitignore` file para awtomatikong harangan ang anumang local configuration files na may passwords kapag nagpu-push kami sa git repository."*

---

## Part 3: Paano sasagutin ang mga posibleng itanong ng Panel (Q&A Cheat Sheet)

* **Q: Paano nagpalit ang Django mula sa SQLite (local) papunta sa PostgreSQL (production)?**
  * **A:** *"Gumamit po kami ng library na `dj_database_url`. Sa loob ng `settings.py`, chine-check ng code kung may environment variable na `DATABASE_URL` na galing sa Render. Kapag mayroon po, PostgreSQL ang ginagamit; kung wala naman po (tulad ng sa local development natin), kusa itong bumabalik sa local SQLite database."*

* **Q:  Ano ang purpose ng `build.sh` file sa project ninyo?**
  * **A:** *"Ito po ang blueprint o automated build script na pinatatakbo ng Render tuwing may bago kaming push sa GitHub. Awtomatiko nitong ini-install ang libraries mula sa `requirements.txt`, pinatatakbo ang database migrations gamit ang `python manage.py migrate` para ma-update ang PostgreSQL tables, at tinitipon ang static files gamit ang `collectstatic`."*

* **Q: Paano niyo siniguro na hindi mag-ooverflow ang file storage ng inyong Render web server?**
  * **A:** *"Dahil free tier at ephemeral ang storage ng Render, ginamit po natin ang `django-cloudinary-storage` na library. Itinuturo nito ang file storage backend ng Django papunta sa Cloudinary APIs, kaya walang local files na naiipon sa server."*
