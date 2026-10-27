import hashlib, secrets, json, pathlib, os, time
import pymysql
root=pathlib.Path(__file__).resolve().parents[1]
config_path=root/'.local-config.json'
if not config_path.exists():
    config_path.write_text(json.dumps({'dbPassword':secrets.token_urlsafe(24),'rootPassword':secrets.token_urlsafe(24),'serviceKey':secrets.token_urlsafe(32),'demoPassword':secrets.token_urlsafe(12)},indent=2))
config=json.loads(config_path.read_text())
try:
    c=pymysql.connect(host='127.0.0.1',port=3307,user='root',password=config['rootPassword'],autocommit=True)
except pymysql.err.OperationalError:
    c=pymysql.connect(host='127.0.0.1',port=3307,user='root',password='',autocommit=True)
    with c.cursor() as q:q.execute('ALTER USER CURRENT_USER() IDENTIFIED BY %s',(config['rootPassword'],))
with c.cursor() as q:
    for statement in (root/'database/schema.sql').read_text(encoding='utf-8-sig').split(';'):
        if statement.strip():q.execute(statement)
    q.execute("CREATE USER IF NOT EXISTS 'smartride'@'127.0.0.1' IDENTIFIED BY %s",(config['dbPassword'],))
    q.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON smartride.* TO 'smartride'@'127.0.0.1'")
    q.execute('SELECT COUNT(*) FROM users')
    if q.fetchone()[0]==0:
        import base64, datetime, random
        def hashed(p):
            salt=secrets.token_bytes(16)
            return '210000:'+base64.b64encode(salt).decode()+':'+base64.b64encode(hashlib.pbkdf2_hmac('sha256',p.encode(),salt,210000)).decode()
        accounts=[('Community Admin','admin@smartride.local','Operations','ADMIN'),('Aarav Sharma','aarav@smartride.local','Engineering','EMPLOYEE'),('Priya Nair','priya@smartride.local','Design','EMPLOYEE'),('Karthik Raj','karthik@smartride.local','Engineering','EMPLOYEE'),('Meera Iyer','meera@smartride.local','People & Culture','EMPLOYEE')]
        for name,email,department,role in accounts:q.execute('INSERT INTO users(name,email,password_hash,department,role) VALUES(%s,%s,%s,%s,%s)',(name,email,hashed(config['demoPassword']),department,role))
        locations=[('Velachery','Tidel Park',12.975,80.22,12.9895,80.249,8,60),('Adyar','Tidel Park',13.0012,80.2565,12.9895,80.249,5,40),('Guindy','DLF IT Park',13.0067,80.2206,13.025,80.176,9,65)]
        today=datetime.datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)
        rng=random.Random(42)
        for offset in range(-28,5):
            day=today+datetime.timedelta(days=offset)
            count=3 if day.weekday()<5 else 1
            for j in range(count):
                origin,destination,olat,olng,dlat,dlng,distance,price=locations[j%3]
                driver=3+j%3; seats=3; taken=(1+j%2) if offset<0 else 0
                status='COMPLETED' if offset<0 else 'OPEN'
                departure=day+datetime.timedelta(minutes=j*15)
                if offset==0:departure=datetime.datetime.now().replace(second=0,microsecond=0)+datetime.timedelta(hours=1,minutes=j*15)
                q.execute('INSERT INTO rides(driver_id,origin,destination,origin_lat,origin_lng,dest_lat,dest_lng,departure,seats,available_seats,price,distance_km,preference,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(driver,origin,destination,olat,olng,dlat,dlng,departure,seats,seats-taken,price,distance,'any',status))
                ride=q.lastrowid
                if offset<0:
                    for passenger in [2,1][:taken]:
                        q.execute('INSERT INTO ride_requests(user_id,origin,destination,origin_lat,origin_lng,dest_lat,dest_lng,departure,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(passenger,origin,destination,olat,olng,dlat,dlng,departure,'BOOKED'))
                        req=q.lastrowid
                        q.execute('INSERT INTO bookings(ride_id,passenger_id,request_id,status) VALUES(%s,%s,%s,%s)',(ride,passenger,req,'COMPLETED'))
                        booking=q.lastrowid
                        f=[rng.uniform(.65,1),rng.uniform(.7,1),rng.uniform(.5,1),1,0.8]
                        q.execute('INSERT INTO match_history(request_id,ride_id,score,features,model_version) VALUES(%s,%s,%s,%s,%s)',(req,ride,round(sum(f)/5*100,1),json.dumps(f),'synthetic-demo'))
                        q.execute('INSERT INTO feedback(booking_id,rating,comment) VALUES(%s,%s,%s)',(booking,rng.choice([3,4,5]),'Synthetic demonstration feedback'))
        q.execute("INSERT INTO audit_log(user_id,action) VALUES(1,'Loaded synthetic demonstration dataset')")
    c.close()
(root/'LOCAL-LOGIN.txt').write_text('SmartRide local demo\nURL: http://localhost:8080/smartride/\n\nAdmin: admin@smartride.local\nEmployee: aarav@smartride.local\nDriver: priya@smartride.local\nPassword for demo accounts: '+config['demoPassword']+'\n\nAll seeded journeys and feedback are synthetic demonstration data.\nDo not publish this file or .local-config.json.\n',encoding='utf-8')
print('Database schema and local demonstration accounts are ready.')
