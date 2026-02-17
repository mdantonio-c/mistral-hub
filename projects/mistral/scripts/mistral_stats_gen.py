import csv

from restapi.connectors import sqlalchemy
from sqlalchemy import text

ROLES = ("Institutional", "User")

EXCLUDE_STAFF_IDS = False

if EXCLUDE_STAFF_IDS:
    EXCLUDE_R_USER_ID = (
        """AND r.user_id NOT IN (1, 2, 3, 4, 5, 6, 61, 186, 314, 357, 489, 702, 725)"""
    )
    EXCLUDE_U_ID = (
        """AND u.id NOT IN (1, 2, 3, 4, 5, 6, 61, 186, 314, 357, 489, 702, 725)"""
    )
else:
    EXCLUDE_R_USER_ID = """"""
    EXCLUDE_U_ID = """"""


def generate_csv(db, csv_file_path, query):
    # Ottieni query
    query_sql = text(query)
    query_result = db.session.execute(query_sql).mappings().all()

    # Se ci sono risultati, prendi le chiavi dal primo risultato
    if query_result:
        fieldnames = query_result[0].keys()
    else:
        raise Exception("no data found")

    # Scrivi i risultati nel file CSV
    with open(csv_file_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in query_result:
            writer.writerow(result)

    print(f"I dati sono stati scritti nel file CSV: {csv_file_path}")


def gen_users_and_reqs_stats(db):
    # Ottieni la data minima `first_login` dagli utenti rilevanti
    min_date_query = text(
        f"""
        SELECT
            to_char(MIN(u.first_login), 'YYYY-MM-01')::date AS min_date
        FROM "user" u
        WHERE 1=1
            {EXCLUDE_U_ID}
            AND u.first_login IS NOT NULL
    """
    )
    res_min_date_query = db.session.execute(min_date_query).mappings().first()
    min_date = res_min_date_query["min_date"]

    # Assicurati che la data minima sia stata trovata
    if not min_date:
        raise ValueError("Nessun valore 'first_login' trovato negli utenti rilevanti")

    # Converti la data in formato stringa se necessario
    min_date_str = min_date.strftime("%Y-%m-%d")

    # We build the statistics query for requests and roles dynamically for every role we got
    # sql_query_roles = text("""
    # SELECT distinct rl.id as id, rl.description as role
    # FROM "role" rl
    # order by rl.id ASC
    # """)
    # roles = db.session.execute(sql_query_roles).mappings().all()

    # This is to construct the part of the query to retrieve requests info related to different roles
    ctes_roles_reqs = ""
    ctes_roles_reqs_joins = ""
    select_roles_reqs_from_ctes = ""
    for role_desc in ROLES:
        # rl_id = role['id']
        # role_desc = role['role']
        for table_title, schedule_condition, table_alias, var_alias in [
            ("TotReqs", "AND 1=1", f"r_{role_desc}_tr", f"role_{role_desc}_tot_reqs"),
            (
                "DirReqs",
                "AND r.schedule_id IS NULL",
                f"r_{role_desc}_dr",
                f"role_{role_desc}_dir_reqs",
            ),
            (
                "SchedReqs",
                "AND r.schedule_id IS NOT NULL",
                f"r_{role_desc}_sr",
                f"role_{role_desc}_sched_reqs",
            ),
        ]:
            ctes_roles_reqs += f"""
    Role_{role_desc}_{table_title} AS (
        SELECT
            COUNT(r.id) as reqs,
            rl.description as role,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        LEFT JOIN "user" u ON u.id = r.user_id
        LEFT JOIN "roles_users" ru on ru.user_id = u.id
        LEFT JOIN "role" rl on ru.role_id = rl.id
        WHERE 1=1
        {EXCLUDE_R_USER_ID}
        {schedule_condition}
        AND rl.description = '{role_desc}'
        GROUP BY rl.description, to_char(r.submission_date, 'YYYY-MM')
    ),
    Cumul_Role_{role_desc}_{table_title} AS (
    SELECT
        COUNT(r.id) as reqs,
        rl.description as role,
        to_char(m.year_month::date, 'YYYY-MM') AS year_month
    FROM
    (SELECT to_date(year_month, 'YYYY-MM') AS year_month
         FROM Months) m
    LEFT JOIN "request" r on to_char(r.submission_date, 'YYYY-MM') <= to_char(m.year_month, 'YYYY-MM')
    LEFT JOIN "user" u ON u.id = r.user_id
    LEFT JOIN "roles_users" ru on ru.user_id = u.id
    LEFT JOIN "role" rl on ru.role_id = rl.id
    WHERE 1=1
    {EXCLUDE_R_USER_ID}
    {schedule_condition}
    AND rl.description = '{role_desc}'
    GROUP BY rl.description, m.year_month
    ),"""

            ctes_roles_reqs_joins += f"""
    LEFT JOIN Role_{role_desc}_{table_title} {table_alias} ON m.year_month = {table_alias}.year_month
    LEFT JOIN Cumul_Role_{role_desc}_{table_title} cumul_{table_alias} ON m.year_month = cumul_{table_alias}.year_month
    """

            select_roles_reqs_from_ctes += f"""
    COALESCE({table_alias}.reqs, 0) AS {var_alias},
    COALESCE(cumul_{table_alias}.reqs, 0) AS cumul_{var_alias},"""

    # This is to construct the part of the query to retrieve all the active users divided by roles
    ctes_roles_users = ""
    ctes_roles_users_joins = ""
    select_roles_users_from_ctes = ""
    for role_desc in ROLES:
        ctes_roles_users += f"""
    Cumul_ActiveUsersRole{role_desc} AS (
        SELECT
            COUNT(DISTINCT u.id) AS users,
            rl.description AS role,
            to_char(m.year_month::date, 'YYYY-MM') AS year_month
        FROM
            (SELECT to_date(year_month, 'YYYY-MM') AS year_month
             FROM Months) m
        LEFT JOIN "user" u ON to_char(u.first_login, 'YYYY-MM') <= to_char(m.year_month, 'YYYY-MM')
        LEFT JOIN "roles_users" ru on ru.user_id = u.id
        LEFT JOIN "role" rl on ru.role_id = rl.id
        WHERE 1=1
            {EXCLUDE_U_ID}
            AND u.first_login IS NOT NULL
            AND rl.description = '{role_desc}'
        GROUP BY rl.description, m.year_month
    ),"""

        ctes_roles_users_joins += f"""
    LEFT JOIN Cumul_ActiveUsersRole{role_desc} cm_us_rl_{role_desc} ON m.year_month = cm_us_rl_{role_desc}.year_month
    """

        select_roles_users_from_ctes += f"""
    COALESCE(cm_us_rl_{role_desc}.users, 0) AS cumul_users_rl_{role_desc},"""

    query = f"""
    WITH Months AS (
        SELECT
            to_char(generate_series('{min_date_str}'::date, CURRENT_DATE, '1 month'), 'YYYY-MM') AS year_month
    ),
    NewUsers AS (
        SELECT
            COUNT(DISTINCT u.id) AS users,
            to_char(u.first_login, 'YYYY-MM') AS year_month
        FROM "user" u
        WHERE 1=1
            {EXCLUDE_U_ID}
            AND u.first_login IS NOT NULL
        GROUP BY to_char(u.first_login, 'YYYY-MM')
    ),
    ActiveUsers AS (
        SELECT
            COUNT(DISTINCT r.user_id) AS users,
            to_char(r.date, 'YYYY-MM') AS year_month
        FROM "login" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
        GROUP BY to_char(r.date, 'YYYY-MM')
    ),
    Cumul_ActiveUsers AS (
        SELECT
            to_char(m.year_month::date, 'YYYY-MM') AS year_month,
            COUNT(DISTINCT u.id) AS users
        FROM
            (SELECT to_date(year_month, 'YYYY-MM') AS year_month
             FROM Months) m
        LEFT JOIN "user" u ON to_char(u.first_login, 'YYYY-MM') <= to_char(m.year_month, 'YYYY-MM')
        WHERE 1=1
            {EXCLUDE_U_ID}
            AND u.first_login IS NOT NULL
        GROUP BY m.year_month
    ),
    {ctes_roles_users}
    TotalRequests AS (
        SELECT
            COUNT(id) as reqs,
            to_char(submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    Cumul_TotalRequests AS (
        SELECT
            to_char(m.year_month::date, 'YYYY-MM') AS year_month,
            COUNT(r.id) as reqs
        FROM
            (SELECT to_date(year_month, 'YYYY-MM') AS year_month
             FROM Months) m
        LEFT JOIN "request" r on to_char(r.submission_date, 'YYYY-MM') <= to_char(m.year_month, 'YYYY-MM')
        LEFT JOIN "user" u ON u.id = r.user_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
        GROUP BY m.year_month
    ),
    {ctes_roles_reqs}
    TotalRequestsObs AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND d.category = 'OBS'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    TotalRequestsFor AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND d.category = 'FOR'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    TotalRequestsRad AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND d.category = 'RAD'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    TotalSuccessfulRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.status != 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    TotalFailedRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.status = 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectRequestsObs AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
            AND d.category = 'OBS'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectRequestsFor AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
            AND d.category = 'FOR'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectRequestsRad AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
            AND d.category = 'RAD'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectSuccessfulRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
            AND r.status != 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    DirectFailedRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NULL
            AND r.status = 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledRequestsObs AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
            AND d.category = 'OBS'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledRequestsFor AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
            AND d.category = 'FOR'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledRequestsRad AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
            AND d.category = 'RAD'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledSuccessfulRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
            AND r.status != 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    ),
    ScheduledFailedRequests AS (
        SELECT
            COUNT(r.id) as reqs,
            to_char(r.submission_date, 'YYYY-MM') as year_month
        FROM "request" r
        WHERE 1=1
            {EXCLUDE_R_USER_ID}
            AND r.schedule_id IS NOT NULL
            AND r.status = 'FAILURE'
        GROUP BY to_char(r.submission_date, 'YYYY-MM')
    )
    SELECT
        m.year_month AS year_month,
        COALESCE(nu.users, 0) AS new_users,
        COALESCE(lu.users, 0) AS active_users,
        COALESCE(cau.users, 0) AS tot_active_users,
        {select_roles_users_from_ctes}
        COALESCE(tr.reqs, 0) AS tot_requests,
        COALESCE(cuml_tr.reqs, 0) AS cumul_tot_requests,
        {select_roles_reqs_from_ctes}
        COALESCE(tro.reqs, 0) AS tot_reqs_obs,
        COALESCE(trf.reqs, 0) AS tot_reqs_for,
        COALESCE(trr.reqs, 0) AS tot_reqs_rad,
        COALESCE(tsr.reqs, 0) AS tot_reqs_succ,
        COALESCE(tfr.reqs, 0) AS tot_reqs_fail,
        COALESCE(dr.reqs, 0) AS direct_reqs,
        COALESCE(dro.reqs, 0) AS dir_reqs_obs,
        COALESCE(drf.reqs, 0) AS dir_reqs_for,
        COALESCE(drr.reqs, 0) AS dir_reqs_rad,
        COALESCE(dsr.reqs, 0) AS dir_reqs_succ,
        COALESCE(dfr.reqs, 0) AS dir_reqs_fail,
        COALESCE(sr.reqs, 0) AS sched_reqs,
        COALESCE(sro.reqs, 0) AS sched_reqs_obs,
        COALESCE(srf.reqs, 0) AS sched_reqs_for,
        COALESCE(srr.reqs, 0) AS sched_reqs_rad,
        COALESCE(ssr.reqs, 0) AS sched_reqs_succ,
        COALESCE(sfr.reqs, 0) AS sched_reqs_fail
    FROM
        Months m
    LEFT JOIN NewUsers nu ON m.year_month = nu.year_month
    LEFT JOIN ActiveUsers lu ON m.year_month = lu.year_month
    LEFT JOIN Cumul_ActiveUsers cau ON m.year_month = cau.year_month
    LEFT JOIN TotalRequests tr ON m.year_month = tr.year_month
    LEFT JOIN Cumul_TotalRequests cuml_tr ON m.year_month = cuml_tr.year_month
    LEFT JOIN TotalRequestsObs tro ON m.year_month = tro.year_month
    LEFT JOIN TotalRequestsFor trf ON m.year_month = trf.year_month
    LEFT JOIN TotalRequestsRad trr ON m.year_month = trr.year_month
    LEFT JOIN TotalSuccessfulRequests tsr ON m.year_month = tsr.year_month
    LEFT JOIN TotalFailedRequests tfr ON m.year_month = tfr.year_month
    LEFT JOIN DirectRequests dr ON m.year_month = dr.year_month
    LEFT JOIN DirectRequestsObs dro ON m.year_month = dro.year_month
    LEFT JOIN DirectRequestsFor drf ON m.year_month = drf.year_month
    LEFT JOIN DirectRequestsRad drr ON m.year_month = drr.year_month
    LEFT JOIN DirectSuccessfulRequests dsr ON m.year_month = dsr.year_month
    LEFT JOIN DirectFailedRequests dfr ON m.year_month = dfr.year_month
    LEFT JOIN ScheduledRequests sr ON m.year_month = sr.year_month
    LEFT JOIN ScheduledRequestsObs sro ON m.year_month = sro.year_month
    LEFT JOIN ScheduledRequestsFor srf ON m.year_month = srf.year_month
    LEFT JOIN ScheduledRequestsRad srr ON m.year_month = srr.year_month
    LEFT JOIN ScheduledSuccessfulRequests ssr ON m.year_month = ssr.year_month
    LEFT JOIN ScheduledFailedRequests sfr ON m.year_month = sfr.year_month
    {ctes_roles_reqs_joins}
    {ctes_roles_users_joins}
    ORDER BY m.year_month DESC
    """

    # Definisci il percorso del file CSV in cui scriverai i dati
    csv_file_path = "users_and_reqs_stats.csv"

    generate_csv(db, csv_file_path, query)


def gen_top_reqs_ranking_stats(db):
    roles_str_joined = "', '".join(ROLES)
    roles_to_analyze = f"""('{roles_str_joined}')"""

    final_query = f"""
    WITH "tot_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
        WHERE
            u.first_login IS NOT NULL
        GROUP BY
            u.id
    ),"dir_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
            AND r.schedule_id IS NULL

        WHERE
            u.first_login IS NOT NULL
        GROUP BY
            u.id
    ),
    "sched_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
            AND r.schedule_id IS NOT NULL
        WHERE
            u.first_login IS NOT NULL
        GROUP BY
            u.id
    ),
    "forec_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
        LEFT JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE
            u.first_login IS NOT NULL
            AND d.category = 'FOR'
        GROUP BY
            u.id
    ),
    "obs_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
        LEFT JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE
            u.first_login IS NOT NULL
            AND d.category = 'OBS'
        GROUP BY
            u.id
    ),
    "rad_reqs" AS
    (
        SELECT
            COUNT(r.id) AS reqs,
            u.id AS user
        FROM
            "user" u
        LEFT JOIN "request" r
            ON u.id = r.user_id
        LEFT JOIN "datasets" d ON jsonb_array_element_text(r.args->'datasets', 0) = d.arkimet_id
        WHERE
            u.first_login IS NOT NULL
            AND d.category = 'RAD'
        GROUP BY
            u.id
    )
    SELECT
        COALESCE(tr.reqs, 0) AS reqs,
        COALESCE(dr.reqs, 0) AS dir_reqs,
        COALESCE(sr.reqs, 0) AS sched_reqs,
        COALESCE(fcr.reqs, 0) AS forec_reqs,
        COALESCE(obr.reqs, 0) AS obs_reqs,
        COALESCE(rar.reqs, 0) AS rad_reqs,
        u.id AS user,
        u.name,
        u.surname,
        u.email,
        rl.description AS role
    FROM
        "user" u
    LEFT JOIN "roles_users" ru
        ON ru.user_id = u.id
    LEFT JOIN "role" rl
        ON ru.role_id = rl.id
    LEFT JOIN "tot_reqs" tr
        ON tr.user = u.id
    LEFT JOIN "dir_reqs" dr
        ON dr.user = u.id
    LEFT JOIN "sched_reqs" sr
        ON sr.user = u.id
    LEFT JOIN "forec_reqs" fcr
        ON fcr.user = u.id
    LEFT JOIN "obs_reqs" obr
        ON obr.user = u.id
    LEFT JOIN "rad_reqs" rar
        ON rar.user = u.id
    WHERE
        u.first_login IS NOT NULL
        AND rl.description IN {roles_to_analyze}
        {EXCLUDE_U_ID}
    ORDER BY
        COALESCE(tr.reqs, 0) DESC, u.surname ASC
    """

    # Definisci il percorso del file CSV in cui scriverai i dati
    csv_path = "top_users_for_reqs_stats.csv"

    # Genera il csv con il top ranking di utenti
    generate_csv(db, csv_path, final_query)


if __name__ == "__main__":
    db_inst = sqlalchemy.get_instance()
    gen_users_and_reqs_stats(db_inst)
    gen_top_reqs_ranking_stats(db_inst)
    db_inst.session.close()
