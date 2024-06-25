from restapi.connectors import sqlalchemy

groups_to_enable_names = ["istituzionali-cfd"]
roles_to_enable_names = ["institutional", "admin_root", "operational"]
datasets_to_enable_names = ["ICON-2I_all2km", "ICON-2I_ita2km"]

db = sqlalchemy.get_instance()

users = db.User.query.all()
users_to_enable_list = []

for u in users:
    # check the group
    if u.belongs_to.shortname in groups_to_enable_names:
        users_to_enable_list.append(u)
        continue
    # check the role
    roles = u.roles
    for role in roles:
        if role.name in roles_to_enable_names:
            users_to_enable_list.append(u)
            continue

for dataset in datasets_to_enable_names:
    # get the dataset
    dataset_entry = db.Datasets.query.filter_by(name=dataset).first()
    if dataset_entry:
        if users_to_enable_list:
            for u in users_to_enable_list:
                # add all the users
                if not dataset_entry.users:
                    dataset_entry.users = [u]
                else:
                    dataset_entry.users.append(u)
                db.session.add(dataset_entry)
                db.session.commit()
