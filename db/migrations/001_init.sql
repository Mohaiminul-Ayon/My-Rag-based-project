create table doctors (
  id uuid primary key,
  source_doctor_id text unique,
  name text not null,
  specialty text,
  qualifications text,
  designation text,
  workplace text,
  bmdc_reg_no text,
  region text,
  source_url text,
  status text not null default 'published',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table chambers (
  id uuid primary key,
  doctor_id uuid not null references doctors(id),
  hospital text,
  address text,
  phone text,
  visiting_hours text,
  created_at timestamptz not null default now()
);

create index doctors_specialty_idx on doctors (specialty);
create index doctors_region_idx on doctors (region);
create index chambers_doctor_id_idx on chambers (doctor_id);
